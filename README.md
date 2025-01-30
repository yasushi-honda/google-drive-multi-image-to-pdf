# google-drive-multi-image-to-pdf

Googleドライブの複数画像を1つのPDFに変換するPythonツール。指定フォルダから画像を取得し、指定順に結合。コントラスト強調で視認性向上も可能。レポート作成等に便利。※既存PDFの結合は非対応。

---

## 特徴

- Googleドライブの指定フォルダから複数の画像（JPEG, PNG）を取得
- 指定された順序で画像を結合し、単一のPDFファイルを作成
- オプションで画像の前処理が可能:
  - コントラスト強調による視認性向上
  - 台形補正機能（試験的機能）
- Cloud Run での実行を想定し、Workload Identity 連携による認証をサポート
- JSON 形式の設定で簡単に操作可能

---

## 動作環境

- Python 3.10 以上

---

## 必要なライブラリ

```bash
pip install -r requirements.txt
```

### `requirements.txt`
```
Flask==2.3.3
Pillow==9.5.0
opencv-python-headless==4.8.0.76
numpy==1.24.0
google-cloud-secret-manager==2.16.2
google-auth>=2.15.0
google-auth-httplib2>=0.1.0
google-api-python-client==2.93.0
gunicorn==20.1.0
```

---

## セットアップ方法

### 1. Google Cloud プロジェクトの準備

1. Google Cloud Platform (GCP) で新規プロジェクトを作成
2. **Google Drive API** を有効化
3. **Cloud Run** を有効化
4. **Artifact Registry** を有効化

---

### 2. 認証設定

#### Workload Identity 連携 (推奨)

1. サービスアカウントを作成（`cloud-run-sa`）
2. IAMロールを設定:
   - `roles/iam.workloadIdentityUser`
   - `roles/storage.admin`
   - `roles/drive.file`
3. Workload Identity プールを作成し、サービスアカウントにバインド

#### Secret Manager 経由の認証（オプション）

1. サービスアカウントの鍵（JSON）を作成
2. Secret Manager に鍵を保存
3. 環境変数で `SERVICE_ACCOUNT_SECRET_NAME` を設定

---

## アプリケーションのデプロイ

### 1. コンテナイメージのビルド

```bash
docker build -t image-to-pdf .
```

### 2. Artifact Registry へのプッシュ

```bash
docker tag image-to-pdf asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/my-repo/image-to-pdf:latest
docker push asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/my-repo/image-to-pdf:latest
```

### 3. Cloud Run へデプロイ

```bash
gcloud run deploy image-to-pdf \
    --image asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/my-repo/image-to-pdf:latest \
    --service-account=cloud-run-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com \
    --region=asia-northeast1 \
    --allow-unauthenticated
```

---

## エンドポイント

### `/convert`

**POSTリクエスト例:**
```json
{
  "key": "your_key",
  "fileOrder": ["画像①", "画像②", "画像③"],
  "applyPerspectiveCorrection": false,
  "applyContrastImprovement": true,
  "name": "output.pdf",
  "sourceFolderId": "your_source_folder_id",
  "folderId": "your_destination_folder_id"
}
```

---

## エラートラブルシューティング

1. **Google Drive API が有効になっていない → `drive.googleapis.com` を有効化**
2. **Cloud Run のサービスアカウントに Drive へのアクセス権がない → Drive フォルダの共有設定を更新**
3. **Artifact Registry に認証エラーが出る → `gcloud auth configure-docker` を実行**

---

## ライセンス

MIT License

---

## コントリビューション

バグ報告や機能提案、プルリクエストなど、歓迎します！

