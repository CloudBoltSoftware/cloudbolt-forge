from utilities.logger import ThreadLogger

logger = ThreadLogger(__name__)

def run_config(xui_version):
    logger.info(f"Azure AD Group s XUI version {xui_version} loaded.")
