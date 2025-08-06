import logging
import os
from logging.handlers import RotatingFileHandler
import sys

def setup_logging():
    # Đảm bảo thư mục logs tồn tại
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Cấu hình logger
    logger = logging.getLogger('patient_management')
    logger.setLevel(logging.DEBUG)

    # Formatter cho log
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Handler cho file log (Rotating để giới hạn kích thước file log)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Handler cho console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    # Thêm handlers vào logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Khởi tạo logger khi module được import
logger = setup_logging()