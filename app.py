from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud import secretmanager
from PIL import Image, ExifTags
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import cv2
import numpy as np
import io
import logging
import json
import time

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ======== グローバル変数・定数設定 ========
SERVICE_ACCOUNT_SECRET_NAME = "projects/715443572768/secrets/service-account-key/versions/latest"
PDF_UPLOAD_MIME_TYPE = 'application/pdf'
DRIVE_URL_TEMPLATE = "https://drive.google.com/file/d/{}/view"
API_SCOPES = ['https://www.googleapis.com/auth/drive']

# ======== Secret Managerから認証情報を取得する関数 ========
def get_service_account_credentials():
    try:
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(name=SERVICE_ACCOUNT_SECRET_NAME)
        service_account_info = json.loads(response.payload.data.decode("UTF-8"))
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=API_SCOPES
        )
        logging.info("Secret Managerからサービスアカウントの認証情報を取得しました。")
        return credentials
    except Exception as e:
        logging.error("サービスアカウントの認証情報取得に失敗しました: %s", e)
        raise

# ======== Google APIの初期化 ========
try:
    credentials = get_service_account_credentials()
    drive_service = build('drive', 'v3', credentials=credentials)
    logging.info("Google Drive APIが正常に初期化されました。")
except Exception as e:
    logging.error("APIの初期化に失敗しました: %s", e)
    raise

# ======== Google Drive内でkeyに基づく画像ファイルのIDを探索する関数 ========
def find_images_by_key(key, source_folder_id, file_order):
    try:
        query = f"'{source_folder_id}' in parents and (mimeType='image/jpeg' or mimeType='image/png')"
        logging.info("使用しているクエリ: %s", query)
        
        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])

        files_dict = {file['name']: file['id'] for file in files}
        logging.info("取得したファイル一覧: %s", files_dict)

        ordered_ids = []
        for order in file_order:
            expected_name_start = f"{key}.{order}"
            matched_file = next((file_id for name, file_id in files_dict.items() if name.startswith(expected_name_start)), None)
            if matched_file:
                ordered_ids.append(matched_file)
                logging.info("ファイル名 %s が見つかりました。ID: %s", expected_name_start, matched_file)
            else:
                logging.warning("ファイル名 %s が見つかりません。", expected_name_start)

        logging.info("取得したファイルID（fileOrderに従った順序付き）: %s", ordered_ids)
        return ordered_ids
    except Exception as e:
        logging.error("ファイル探索中にエラーが発生しました: %s", e)
        raise

# ======== Google Driveから画像ファイルをダウンロードする関数 ========
def download_image(file_id, retries=3, delay=2):
    for attempt in range(retries):
        try:
            request = drive_service.files().get_media(fileId=file_id)
            file_data = io.BytesIO()
            downloader = MediaIoBaseDownload(file_data, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            file_data.seek(0)
            logging.info("ファイルID %s の画像をダウンロードしました。", file_id)
            return Image.open(file_data)
        except Exception as e:
            logging.error("画像ダウンロードに失敗しました (試行 %d/%d): %s", attempt + 1, retries, e)
            time.sleep(delay)
    raise Exception(f"ファイルID {file_id} の画像ダウンロードに最終試行で失敗しました。")

# ======== 画像の向きをExif情報に基づいて修正する関数 ========
def fix_image_orientation(image):
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
                break
        exif = image._getexif()
        if exif is not None:
            orientation = exif.get(orientation)
            if orientation == 3:
                image = image.rotate(180, expand=True)
            elif orientation == 6:
                image = image.rotate(-90, expand=True)
            elif orientation == 8:
                image = image.rotate(90, expand=True)
    except Exception as e:
        logging.warning("向き修正に失敗しました: %s", e)
    return image

# ======== 画像の台形補正を行う関数 ========
def correct_perspective(image):
    try:
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2GRAY)
        edged = cv2.Canny(gray, 50, 200)
        contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        for contour in contours:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            if len(approx) == 4:
                doc_cnts = approx
                break
        else:
            logging.warning("台形補正用の輪郭が見つかりませんでした。")
            return image

        pts = doc_cnts.reshape(4, 2)
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0], rect[2] = pts[np.argmin(s)], pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1], rect[3] = pts[np.argmin(diff)], pts[np.argmax(diff)]
        (tl, tr, br, bl) = rect

        maxWidth, maxHeight = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl))), int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
        dst = np.array([[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(np.array(image), M, (maxWidth, maxHeight))
        return Image.fromarray(warped)
    except Exception as e:
        logging.error("台形補正に失敗しました: %s", e)
        return image

# ======== 画像のコントラスト改善を行う関数 ========
def improve_contrast(image):
    try:
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2GRAY)
        equalized = cv2.equalizeHist(gray)
        return Image.fromarray(equalized)
    except Exception as e:
        logging.error("コントラスト改善に失敗しました: %s", e)
        return image

# ======== Google DriveにPDFファイルをアップロードする関数 ========
def upload_pdf_to_drive(pdf_buffer, pdf_name, folder_id):
    try:
        pdf_buffer.seek(0)
        media = MediaIoBaseUpload(pdf_buffer, mimetype=PDF_UPLOAD_MIME_TYPE, resumable=True)
        file_metadata = {'name': pdf_name, 'parents': [folder_id], 'mimeType': PDF_UPLOAD_MIME_TYPE}
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        pdf_url = DRIVE_URL_TEMPLATE.format(file['id'])
        logging.info("Google DriveにPDFをアップロードしました: %s", pdf_url)
        return pdf_url
    except Exception as e:
        logging.error("Google DriveへのPDFアップロードに失敗しました: %s", e)
        raise

# ======== メインのエンドポイント ========
@app.route('/convert', methods=['POST'])
def convert_images_to_pdf():
    try:
        data = request.get_json()
        logging.info("受信したペイロード内容: %s", data)

        key = data.get('key')
        file_order = data.get('fileOrder', [])
        apply_perspective_correction = data.get('applyPerspectiveCorrection', False)
        apply_contrast_improvement = data.get('applyContrastImprovement', False)
        pdf_name = data.get('name', 'combined_output.pdf')
        source_folder_id = data.get('sourceFolderId')
        destination_folder_id = data.get('folderId')

        if not all([key, file_order, pdf_name, source_folder_id, destination_folder_id]):
            missing_params = [param for param in ['key', 'file_order', 'pdf_name', 'source_folder_id', 'destination_folder_id'] if not data.get(param)]
            logging.error("Missing required parameters: %s", ", ".join(missing_params))
            return jsonify({'error': f'Missing required parameters: {", ".join(missing_params)}'}), 400

        file_ids = find_images_by_key(key, source_folder_id, file_order)

        images = []
        for file_id in file_ids:
            image = download_image(file_id)
            image = fix_image_orientation(image)
            if apply_perspective_correction:
                image = correct_perspective(image)
            if apply_contrast_improvement:
                image = improve_contrast(image)
            images.append(image.convert('RGB'))

        if images:
            pdf_buffer = io.BytesIO()
            images[0].save(pdf_buffer, format='PDF', save_all=True, append_images=images[1:])
            pdf_url = upload_pdf_to_drive(pdf_buffer, pdf_name, destination_folder_id)
            logging.info("PDF変換が成功しました。URL: %s", pdf_url)
            return jsonify({'message': 'PDF conversion completed successfully', 'pdf_url': pdf_url}), 200
        else:
            return jsonify({'error': 'No images available for PDF conversion'}), 500

    except Exception as e:
        logging.exception("PDF変換中にエラーが発生しました。")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
