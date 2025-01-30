# google-drive-multi-image-to-pdf
Googleドライブの複数画像を1つのPDFに変換するPythonツール。指定フォルダから画像を取得し、指定順に結合。コントラスト強調で視認性向上も可能。レポート作成等に便利。※既存PDFの結合は非対応。

# google-drive-multi-image-to-pdf

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Googleドライブ上の指定フォルダから複数の画像を取得し、それらを1つのPDFファイルに結合する Python ツールです。

## 特徴

*   Googleドライブの指定フォルダから複数の画像（JPEG, PNG）を取得
*   指定された順序で画像を結合し、単一のPDFファイルを作成
*   オプションで画像の前処理が可能:
    *   コントラスト強調による視認性向上
*   Cloud Run での実行を想定し、Workload Identity 連携による認証をサポート (Secret Manager も利用可能)
*   JSON 形式の設定で簡単に操作可能

## 動作環境

*   Python 3.10

## 必要なライブラリ
Use code with caution.
Markdown
Flask==2.3.3
Pillow==9.5.0
opencv-python-headless==4.8.0.76
numpy==1.24.0
google-cloud-secret-manager==2.16.2 (Secret Manager 使用時)
google-auth>=2.15.0
google-auth-httplib2>=0.1.0
google-api-python-client==2.93.0
gunicorn==20.1.0

インストール:

```bash
pip install -r requirements.txt
Use code with caution.
セットアップ方法
1. Google Cloud プロジェクトの作成
Google Cloud Platform (GCP) でプロジェクトを作成します。

プロジェクトで Google Drive API を有効化します。

2. 認証情報の設定
このアプリケーションは、Google Drive API にアクセスするためにサービスアカウントを使用します。以下のいずれかの方法で認証情報を設定してください。

A. Workload Identity 連携 (推奨)
サービスアカウントの作成:

GCP Console で、IAM と管理 > サービスアカウント に移動します。

「サービスアカウントを作成」をクリックし、サービスアカウント名 (例: drive-to-pdf-sa) を入力します。

サービスアカウント ID を確認して「作成して続行」をクリックします。

このサービスアカウントに以下のロールを付与します:

閲覧者 (プロジェクト全体、または対象のGoogle Drive フォルダ)

Workload Identity ユーザー (サービスアカウントに対して)

「完了」をクリックします。

Workload Identity プールの作成 (未作成の場合):

IAM と管理 > ワークロード ID 連携 に移動します。

プロンプトに従って、Workload Identity プールを作成します。

Workload Identity プロバイダの作成 (未作成の場合):

作成したプールの画面で、「プロバイダを追加」をクリックします。

プロバイダのタイプとして「その他」を選択します。

プロバイダ名とプロバイダ ID を入力します。プロバイダ ID は https://iam.googleapis.com/projects/<プロジェクト番号>/locations/global/workloadIdentityPools/<プール名>/providers/<プロバイダ名> の形式になります。

サービスアカウントへの権限付与:

作成した Workload Identity プロバイダの画面で、「アクセス権を付与」をクリックします。

「プリンシパル」に、前の手順で作成したサービスアカウント (例: serviceAccount:<プロジェクト番号>.svc.id.goog[<名前空間>/<サービスアカウント名>]) を指定します。名前空間は通常 default ですが、適宜変更してください。

「ロール」に「Workload Identity ユーザー」を選択します。

「保存」をクリックします。

アプリケーションのコード修正:

app.py 内の get_service_account_credentials 関数を、Workload Identity を使用するように修正します。以下を参考にしてください:

from google.auth import default, exceptions

def get_service_account_credentials():
    try:
        credentials, project = default()
        logging.info("Workload Identity 連携で認証情報を取得しました。")
        return credentials
    except exceptions.DefaultCredentialsError as e:
        logging.error("認証情報の取得に失敗しました: %s", e)
        raise
Use code with caution.
Python
Cloud Run へのデプロイ:

アプリケーションをコンテナ化し、Cloud Run にデプロイします。デプロイ時に、前の手順で作成したサービスアカウントを指定します。

B. Secret Manager (非推奨)
サービスアカウントキーの作成:

IAM > サービスアカウント でサービスアカウントを作成または選択します。

「キー」タブで「鍵を追加」>「新しい鍵を作成」を選択し、キーのタイプとして「JSON」を選択します。

JSON キーファイルがダウンロードされます。このファイルは安全に保管してください。

Secret Manager にシークレットを作成:

GCP Console で、セキュリティ > Secret Manager に移動します。

「シークレットを作成」をクリックし、シークレット名 (例: service-account-key) を入力します。

「シークレットの値」に、先ほどダウンロードした JSON キーファイルの内容を貼り付けます。

「シークレットを作成」をクリックします。

サービスアカウントに権限を付与:

作成したシークレットの「権限」タブで、「プリンシパルを追加」をクリックします。

「新しいプリンシパル」に、サービスアカウントのメールアドレスを入力します。

「ロール」に「Secret Manager のシークレットへのアクセス権」を選択します。

「保存」をクリックします。

環境変数の設定:

SERVICE_ACCOUNT_SECRET_NAME 環境変数に、Secret Manager に作成したシークレットのフルパス (例: projects/<プロジェクト番号>/secrets/service-account-key/versions/latest) を設定します。

3. 環境変数の設定
以下の環境変数を設定する必要があります。

SERVICE_ACCOUNT_SECRET_NAME (Secret Manager 使用時): Secret Manager に保存したサービスアカウントキーのシークレット名。

GOOGLE_APPLICATION_CREDENTIALS(Workload Identity利用時に、ローカル環境で実行する場合のみ): ローカル環境でサービスアカウントキーを使用する場合はそのパスを設定します

4. アプリケーションの実行
gunicorn -b 0.0.0.0:8080 app:app --timeout 120 --workers 3
Use code with caution.
Bash
5. リクエストの送信
以下の JSON ペイロードを使用して、/convert エンドポイントに POST リクエストを送信します。

{
  "key": "your_key",
  "fileOrder": [1, 2, 3],
  "applyPerspectiveCorrection": false,
  "applyContrastImprovement": true,
  "name": "output.pdf",
  "sourceFolderId": "your_source_folder_id",
  "folderId": "your_destination_folder_id"
}
Use code with caution.
Json
key: Googleドライブ上でファイルを識別するためのキー

fileOrder: PDF 内の画像順序を指定する番号の配列

applyPerspectiveCorrection: true に設定すると、台形補正を適用 (現状、十分に機能しない可能性があります)

applyContrastImprovement: true に設定すると、コントラスト強調を適用

name: 出力する PDF ファイル名

sourceFolderId: 読み込み元の Google ドライブフォルダ ID

folderId: PDFの保存先 Google ドライブフォルダ ID

注意事項
このツールは既存の PDF ファイルを結合する機能はありません。複数の画像を 1 つの PDF にまとめることに特化しています。

台形補正機能は試験的なものであり、十分に機能しない可能性があります。

ライセンス
MIT License

コントリビューション
バグ報告や機能提案、プルリクエストなど、歓迎します。

**ポイント:**

*   **冒頭にリポジトリ名、概要、ライセンスバッジを配置。**
*   **必要なライブラリとそのインストール方法を明記。**
*   **Workload Identity 連携と Secret Manager の両方の認証方法を説明。**
    *   Workload Identity 連携を推奨し、詳細な手順を記述。
    *   Secret Manager は非推奨とし、簡潔な説明にとどめる。
*   **環境変数の設定方法を説明。**
*   **アプリケーションの実行方法を記述。**
*   **リクエストの送信方法とパラメータの説明を記述。**
*   **注意事項として、既存 PDF の結合はできないこと、台形補正が不十分な可能性があることを明記。**
*   **ライセンスとコントリビューションについての情報を追加。**
