import base64
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.file.file import File
from sandbox_fusion import run_code
from sandbox_fusion.models import RunCodeRequest

languages = [
    "python",
    "cpp",
    "nodejs",
    "go",
    "go_test",
    "java",
    "php",
    "csharp",
    "bash",
    "typescript",
    "sql",
    "rust",
    "cuda",
    "lua",
    "R",
    "perl",
    "D_ut",
    "ruby",
    "scala",
    "julia",
    "pytest",
    "junit",
    "kotlin_script",
    "jest",
    "verilog",
    "python_gpu",
    "lean",
    "swift",
    "racket",
]


class RunCodeTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:

        code: str = tool_parameters.get("code", None)
        language: str = tool_parameters.get("language", None)
        run_timeout: str = tool_parameters.get("timeout", None)

        files: list[File] = tool_parameters.get("files", [])
        fetch_files_str: str = tool_parameters.get("fetch_files", "")

        if not code or not language:
            yield self.create_json_message(
                {"error": "Code and language parameters are required."}
            )
            yield self.create_text_message(
                "Missing required parameters: 'code' and 'language'."
            )

        if language.strip().lower() not in languages:
            yield self.create_json_message(
                {"error": f"Unsupported language: {language}"}
            )
            yield self.create_text_message(
                f"Unsupported language: {language}. Supported languages are: {', '.join(languages)}"
            )

        files_dict = {}
        if files and isinstance(files, list):
            files_dict = {
                file.filename: base64.b64encode(file.blob).decode("utf-8")
                for file in files
            }
            # for file in files:
            #     print(file.model_dump())

        fetch_files = [
            file.strip() for file in fetch_files_str.split(",") if file.strip()
        ]

        res = run_code(
            RunCodeRequest(
                code=code,
                language=language,
                files=files_dict if files else {},
                fetch_files=fetch_files,
                run_timeout=float(run_timeout) if run_timeout else None,
            ),
            endpoint=self.runtime.credentials.get(
                "SANDBOX_FUSION_ENDPOINT", "http://localhost:8080"
            ),
        )

        yield self.create_text_message(res.message)
        yield self.create_json_message(res.run_result.dict())

        if fetch_files_str:
            IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'}
            IMAGE_MIME_TYPES = {
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'gif': 'image/gif',
                'bmp': 'image/bmp',
                'webp': 'image/webp',
                'svg': 'image/svg+xml',
            }

            for file_name, file_content in res.files.items():
                file_extension = file_name.split('.')[-1].lower() if '.' in file_name else ''
                mime_type = IMAGE_MIME_TYPES.get(file_extension, 'application/octet-stream')

                if file_extension in IMAGE_EXTENSIONS:
                    message_type = ToolInvokeMessage.MessageType.IMAGE
                    blob = base64.b64decode(file_content)
                else:
                    message_type = ToolInvokeMessage.MessageType.BLOB
                    blob = file_content.encode() if isinstance(file_content, str) else file_content

                blog_message = self.response_type(
                    type=message_type,
                    message=ToolInvokeMessage.BlobMessage(blob=blob),
                    meta={"filename": file_name, 'mime_type': mime_type},
                )
                yield blog_message