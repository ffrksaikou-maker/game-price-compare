@echo off
rem XからBOX買取価格を取得してGitHubへ反映する(CIはCloudflareで弾かれるためローカル実行)
cd /d C:\Users\fifty\game-price-compare
set PYTHONIOENCODING=utf-8
python -m scripts.fetch_x_prices --push >> data\x_state\fetch.log 2>&1
