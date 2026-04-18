class SessionInfo:
    def __init__(
        self,
        valid=False,
        session_id=0,
        title="",
        class_name="",
        token="",
        allow_duplicates=False,
    ):
        self.valid = valid
        self.id = session_id
        self.title = title
        self.class_name = class_name
        self.token = token
        self.allow_duplicates = allow_duplicates

    @classmethod
    def from_dict(cls, payload):
        payload = payload or {}
        return cls(
            valid=bool(payload),
            session_id=payload.get("id", 0),
            title=payload.get("title", ""),
            class_name=payload.get("class_name", ""),
            token=payload.get("session_token", ""),
            allow_duplicates=payload.get("allow_duplicates", False),
        )


class StudentInfo:
    def __init__(
        self,
        valid=False,
        student_id=0,
        student_code="",
        full_name="",
        class_name="",
        fingerprint_template_id=0,
    ):
        self.valid = valid
        self.id = student_id
        self.student_code = student_code
        self.full_name = full_name
        self.class_name = class_name
        self.fingerprint_template_id = fingerprint_template_id

    @classmethod
    def from_dict(cls, payload):
        payload = payload or {}
        return cls(
            valid=bool(payload),
            student_id=payload.get("id", 0),
            student_code=payload.get("student_code", ""),
            full_name=payload.get("full_name", ""),
            class_name=payload.get("class_name", ""),
            fingerprint_template_id=payload.get("fingerprint_template_id", 0),
        )


class DeviceCommandInfo:
    def __init__(
        self,
        available=False,
        command_id=0,
        command_type="",
        student_id=0,
        student_code="",
    ):
        self.available = available
        self.id = command_id
        self.type = command_type
        self.student_id = student_id
        self.student_code = student_code

    @classmethod
    def from_dict(cls, payload):
        payload = payload or {}
        command_payload = payload.get("payload", {}) or {}
        return cls(
            available=bool(payload),
            command_id=payload.get("id", 0),
            command_type=payload.get("type", ""),
            student_id=command_payload.get("student_id", 0),
            student_code=command_payload.get("student_code", ""),
        )


class GenericResult:
    def __init__(self, ok=False, message=""):
        self.ok = ok
        self.message = message

    @classmethod
    def from_response(cls, payload, default_error="request failed"):
        payload = payload or {}
        message = payload.get("error") or payload.get("message") or (default_error if not payload.get("ok") else "ok")
        return cls(ok=bool(payload.get("ok")), message=message)
