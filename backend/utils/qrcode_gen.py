import qrcode
import base64
from io import BytesIO


def generate_team_qrcode(team_name: str, class_name: str, url: str) -> str:
    """
    生成小组二维码，返回 base64 编码的 PNG 图片。
    扫码后跳转到小组实践内容的公开页面。
    """
    qr_data = f"{url}"
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return base64.b64encode(buffer.getvalue()).decode("utf-8")
