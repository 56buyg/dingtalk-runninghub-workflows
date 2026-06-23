def main(locals):
    import json
    import mimetypes
    import os
    import tempfile
    import uuid
    from pathlib import Path
    from urllib.error import HTTPError
    from urllib.parse import urlencode, urlparse
    from urllib.request import Request, urlopen

    API_BASE = "https://www.runninghub.cn"

    # Configure each RunningHub app here once.
    # Fill node_id / field_name from RunningHub's nodeInfoList.
    APP_CONFIG = {
        "\u6587\u751f\u56fe": {
            "webapp_id": "2048647046302801921",
            "prompt": {"node_id": "3", "field_name": "text"},
            "aspect_ratio": {"node_id": "1", "field_name": "aspectRatio"},
            "resolution": {"node_id": "1", "field_name": "resolution"},
            # Leave empty when the app has no native quantity node.
            # The script will submit multiple tasks instead.
            "image_count": {"node_id": "", "field_name": ""},
            "negative_prompt": {"node_id": "", "field_name": ""},
            "image": {"node_id": "", "field_name": ""},
        },
        "\u56fe\u751f\u56fe": {
            "webapp_id": "2061356087495974914",
            "prompt": {"node_id": "", "field_name": ""},
            "aspect_ratio": {"node_id": "", "field_name": ""},
            "resolution": {"node_id": "", "field_name": ""},
            "image_count": {"node_id": "", "field_name": ""},
            "negative_prompt": {"node_id": "", "field_name": ""},
            "image": {"node_id": "", "field_name": ""},
        },
    }
    APP_NAME_TO_ID = {name: cfg["webapp_id"] for name, cfg in APP_CONFIG.items()}
    APP_CONFIG_BY_ID = {cfg["webapp_id"]: cfg for cfg in APP_CONFIG.values()}

    def pick(*names, default=""):
        if isinstance(locals, dict):
            for name in names:
                if locals.get(name) not in (None, ""):
                    return locals.get(name)
            for box in ("input", "inputs", "params", "data"):
                child = locals.get(box)
                if isinstance(child, dict):
                    for name in names:
                        if child.get(name) not in (None, ""):
                            return child.get(name)
        return default

    def scalar(value):
        if value in (None, ""):
            return ""
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, list):
            return scalar(value[0]) if value else ""
        if isinstance(value, dict):
            for key in ("value", "text", "content", "url", "downloadUrl", "fileUrl", "name", "id"):
                if value.get(key) not in (None, ""):
                    return scalar(value.get(key))
            return json.dumps(value, ensure_ascii=False)
        return str(value).strip()

    def app_label(value):
        if not value:
            return ""
        if isinstance(value, str):
            text = value.strip()
            try:
                return app_label(json.loads(text))
            except Exception:
                return text
        if isinstance(value, list):
            return app_label(value[0]) if value else ""
        if isinstance(value, dict):
            for key in ("name", "text", "value"):
                if value.get(key) not in (None, ""):
                    return app_label(value.get(key))
        return scalar(value)

    def clean_webapp_id(value):
        text = scalar(value).strip()
        if "/" in text:
            text = text.rstrip("/").split("/")[-1]
        if "?" in text:
            text = text.split("?")[0]
        return text.strip()

    def http_bytes(req, timeout=60):
        try:
            with urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            raise Exception("HTTP %s: %s" % (exc.code, body))

    def req_json(method, url, params=None, body=None, data=None, headers=None, timeout=60):
        if params:
            url += ("&" if "?" in url else "?") + urlencode(params)
        headers = dict(headers or {})
        raw_body = data
        if body is not None:
            raw_body = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        raw = http_bytes(Request(url, data=raw_body, headers=headers, method=method), timeout)
        return json.loads(raw.decode("utf-8"))

    def first_media(value):
        if not value:
            return ""
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return ""
            try:
                return first_media(json.loads(text))
            except Exception:
                return text
        if isinstance(value, list):
            return first_media(value[0]) if value else ""
        if isinstance(value, dict):
            for key in ("downloadUrl", "url", "fileUrl", "previewUrl", "path"):
                if value.get(key):
                    return str(value[key]).strip()
        return str(value).strip()

    def upload_file(api_key, image_value):
        media = first_media(image_value)
        if not media:
            return ""
        temp_path = None
        file_path = media
        if media.startswith(("http://", "https://")):
            suffix = Path(urlparse(media).path).suffix or ".bin"
            content = http_bytes(Request(media, method="GET"), 90)
            handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            try:
                handle.write(content)
                temp_path = handle.name
                file_path = temp_path
            finally:
                handle.close()

        path = Path(file_path)
        if not path.exists():
            raise Exception("input image is not a downloadable URL or local path: %s" % media)

        boundary = "----RH%s" % uuid.uuid4().hex
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        lb = b"\r\n"
        form = bytearray()
        for name, val in {"apiKey": api_key, "fileType": "input"}.items():
            form += ("--%s" % boundary).encode() + lb
            form += ('Content-Disposition: form-data; name="%s"' % name).encode() + lb + lb
            form += str(val).encode() + lb
        form += ("--%s" % boundary).encode() + lb
        form += ('Content-Disposition: form-data; name="file"; filename="%s"' % path.name).encode() + lb
        form += ("Content-Type: %s" % mime_type).encode() + lb + lb
        form += path.read_bytes() + lb
        form += ("--%s--" % boundary).encode() + lb

        try:
            result = req_json(
                "POST",
                API_BASE + "/task/openapi/upload",
                data=bytes(form),
                headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary},
                timeout=120,
            )
            if result.get("msg") != "success":
                raise Exception("RunningHub upload failed: %s" % result)
            return result["data"]["fileName"]
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

    def get_nodes(api_key, webapp_id):
        result = req_json(
            "GET",
            API_BASE + "/api/webapp/apiCallDemo",
            params={"apiKey": api_key, "webappId": webapp_id},
        )
        data = result.get("data")
        if not isinstance(data, dict):
            raise Exception("RunningHub did not return nodeInfoList: %s" % result)
        nodes = data.get("nodeInfoList", [])
        if not isinstance(nodes, list):
            raise Exception("Invalid nodeInfoList response: %s" % result)
        return nodes

    def simple_nodes(nodes):
        items = []
        for n in nodes:
            items.append({
                "nodeId": n.get("nodeId"),
                "fieldName": n.get("fieldName"),
                "fieldType": n.get("fieldType"),
                "fieldValue": n.get("fieldValue"),
            })
        return items

    def set_target(nodes, target, value, label):
        node_id = str(target.get("node_id") or "").strip()
        field_name = str(target.get("field_name") or "").strip()
        if not value:
            return 0
        if not node_id or not field_name:
            return -1
        for n in nodes:
            if str(n.get("nodeId")) == node_id and str(n.get("fieldName")) == field_name:
                n["fieldValue"] = value
                return 1
        raise Exception("%s target not found: node_id=%s field_name=%s" % (label, node_id, field_name))

    def normalize_aspect_ratio(value):
        text = scalar(value)
        return text.replace("\uff1a", ":").replace(" ", "")

    def parse_int(value, default_value=1):
        text = scalar(value).strip()
        if not text:
            return default_value
        digits = ""
        for ch in text:
            if ch.isdigit():
                digits += ch
            elif digits:
                break
        return int(digits) if digits else default_value

    def clamp_image_count(value):
        count = parse_int(value, 1)
        if count < 1:
            return 1
        if count > 8:
            return 8
        return count

    try:
        api_key = scalar(pick("RUNNINGHUB_API_KEY", "api_key", "apiKey", "API_KEY", "Api_Key"))
        raw_webapp_id = pick("RUNNINGHUB_WEBAPP_ID", "webapp_id", "ZOUoE4b")
        webapp_id = clean_webapp_id(raw_webapp_id)
        app_name = app_label(pick("RUNNINGHUB_APP_NAME", "app_name", "\u5e94\u7528"))
        prompt = scalar(pick("RUNNINGHUB_PROMPT", "prompt", "\u63d0\u793a\u8bcd", "Kj9TqrL"))
        aspect_ratio = normalize_aspect_ratio(pick("RUNNINGHUB_ASPECT_RATIO", "aspect_ratio", "\u6bd4\u4f8b"))
        resolution = scalar(pick("RUNNINGHUB_RESOLUTION", "RUNNINGHUB_SIZE", "resolution", "size", "\u5927\u5c0f"))
        image_count = clamp_image_count(pick(
            "RUNNINGHUB_IMAGE_COUNT",
            "RUNNINGHUB_BATCH_SIZE",
            "image_count",
            "\u6570\u91cf",
            "\u5f20\u6570",
            "\u751f\u6210\u6570\u91cf",
            "\u751f\u6210\u56fe\u7247\u6570\u91cf",
            default="1",
        ))
        negative_prompt = scalar(pick("RUNNINGHUB_NEGATIVE_PROMPT", "negative_prompt", "\u8d1f\u9762\u63d0\u793a\u8bcd", "\u8d1f\u9762\u63d0\u793a\u8bcd\uff08\u53ef\u4e0d\u586b\uff09", "59F2Yig"))
        input_image = pick("RUNNINGHUB_INPUT_IMAGE", "input_image", "\u8f93\u5165\u56fe\u7247", "7phsS86")

        if not api_key:
            raise Exception("Missing RUNNINGHUB_API_KEY")
        if not webapp_id and app_name in APP_NAME_TO_ID:
            webapp_id = APP_NAME_TO_ID[app_name]
        if webapp_id not in APP_CONFIG_BY_ID:
            raise Exception("Unknown webapp_id: %s. Add it to APP_CONFIG." % webapp_id)
        app = APP_CONFIG_BY_ID[webapp_id]
        app_label_for_debug = app_name or webapp_id
        if not prompt:
            raise Exception("Prompt is empty. Bind RUNNINGHUB_PROMPT to the table field.")

        nodes = get_nodes(api_key, webapp_id)

        prompt_result = set_target(nodes, app.get("prompt", {}), prompt, "prompt")
        if prompt_result == -1:
            return {
                "success": True,
                "ok": False,
                "task_id": "",
                "output_urls": "",
                "error_message": "APP_CONFIG missing prompt node. Fill node_id/field_name for webapp_id=%s." % webapp_id,
                "debug_info": json.dumps(simple_nodes(nodes), ensure_ascii=False),
            }

        set_target(nodes, app.get("negative_prompt", {}), negative_prompt, "negative_prompt")
        set_target(nodes, app.get("aspect_ratio", {}), aspect_ratio, "aspect_ratio")
        set_target(nodes, app.get("resolution", {}), resolution, "resolution")
        count_target = app.get("image_count", {})
        has_native_count = bool(count_target.get("node_id") and count_target.get("field_name"))
        if has_native_count:
            set_target(nodes, count_target, image_count, "image_count")

        uploaded = upload_file(api_key, input_image)
        image_result = set_target(nodes, app.get("image", {}), uploaded, "image")
        if uploaded and image_result == -1:
            return {
                "success": True,
                "ok": False,
                "task_id": "",
                "output_urls": "",
                "error_message": "APP_CONFIG missing image node. Fill node_id/field_name for webapp_id=%s." % webapp_id,
                "debug_info": json.dumps(simple_nodes(nodes), ensure_ascii=False),
            }

        submit_times = 1 if has_native_count else image_count
        task_ids = []
        for _ in range(submit_times):
            submit = req_json(
                "POST",
                API_BASE + "/task/openapi/ai-app/run",
                body={"webappId": webapp_id, "apiKey": api_key, "nodeInfoList": nodes},
            )
            if submit.get("code") != 0:
                raise Exception("RunningHub submit failed: %s" % submit)
            task_ids.append(str(submit["data"]["taskId"]))
        task_id = "\n".join(task_ids)
        count_strategy = "native_node" if has_native_count else "repeat_submit"
        return {
            "success": True,
            "ok": True,
            "provider": "runninghub",
            "external_id": task_id,
            "task_id": task_id,
            "output_urls": "",
            "error_message": "",
            "debug_info": "submitted only; app=%s; webapp_id=%s; prompt_target=%s/%s" % (
                app_label_for_debug,
                webapp_id,
                app.get("prompt", {}).get("node_id"),
                app.get("prompt", {}).get("field_name"),
            ) + "; aspect_ratio=%s; resolution=%s; image_count=%s; count_strategy=%s" % (
                aspect_ratio,
                resolution,
                image_count,
                count_strategy,
            ),
        }
    except Exception as exc:
        return {
            "success": True,
            "ok": False,
            "provider": "runninghub",
            "external_id": "",
            "task_id": "",
            "output_urls": "",
            "error_message": str(exc),
            "debug_info": "",
        }
