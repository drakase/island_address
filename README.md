# 離島住所生成ツール

## 概要
* 国土交通省が提供する離島振興対策実施地域データと位置参照情報を利用して、都道府県単位で離島住所(都道府県 + 市町村名 + 丁目)一覧を生成します

## 入出力データ
### 入力データ
* [離島振興対策実施地域データ](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A19-v4_0.html)
  * 離島の緯度経度を得るために必要です
  * __GeoJSON形式(平成29年)のデータのみ対応しています__
  * 例えば、長崎県の離島住所一覧を生成する場合は以下のデータをダウンロードします
    * A19-17_42_GML.zip
* [位置参照情報](https://nlftp.mlit.go.jp/cgi-bin/isj/dls/_choose_method.cgi)
  * 住所と緯度経度の対応を得るために必要です
    * 街区レベルと大字・町丁目レベルのデータが必要です
  * 例えば、長崎県の離島住所一覧を生成する場合は以下のデータをダウンロードします
    1. 都道府県単位ボタンを押下し、「長崎」を選択
    2. 「全て」(街区レベルと大字・町丁目レベル)を選択
    3. 同意してダウンロード
      * 街区レベル: 42000-21.0a.zip
      * 大字・町丁目レベル: 42000-16.0b.zip
### 出力データ
* 以下のようなCSV形式で離島住所一覧が保存されます(1行目はヘッダ)
```csv
レベル,都道府県名,市区町村名,大字・丁目名,小字・通称名,街区符号・地番,離島ID,行政区域コード,支庁・振興局名,郡・政令都市名,原典市区町村名,指定地域名,島名,住所
街区,長崎県,五島市,籠淵町,,44,42030,42211,,,五島市,五島列島,福江島,長崎県五島市籠淵町４４
街区,長崎県,五島市,籠淵町,,1116,42030,42211,,,五島市,五島列島,福江島,長崎県五島市籠淵町１１１６
街区,長崎県,五島市,籠淵町,,1155,42030,42211,,,五島市,五島列島,福江島,長崎県五島市籠淵町１１５５
街区,長崎県,五島市,籠淵町,,1162,42030,42211,,,五島市,五島列島,福江島,長崎県五島市籠淵町１１６２
街区,長崎県,五島市,籠淵町,,1165,42030,42211,,,五島市,五島列島,福江島,長崎県五島市籠淵町１１６５
```

## 実行方法
* Python(バージョン3.10以上推奨)がインストールされた環境で以下を実行してください
  * ここでは長崎県の例を示します
```bash
git clone https://github.com/drakase/island_address.git
cd island_address

# 【初回のみ】実行環境を構築します
. ./setup.sh

# 適宜ディレクトリを作成して、入力データを配置します
# 離島振興対策実施地域データ: island_polygon/A19-17_42_GML.zip
# 位置参照情報(街区レベル): geocoding/42000-21.0a.zip
# 位置参照情報(大字・町丁目レベル): geocoding/42000-16.0b.zip

# 都道府県単位で離島住所一覧を生成します
. ./make_island_address.sh \
    island_polygon/A19-17_42_GML.zip \
    geocoding/42000-21.0a.zip \
    geocoding/42000-16.0b.zip \
    island_address/42_nagasaki.csv

# この例では、island_address/42_nagasaki.csv に長崎県の離島住所一覧が保存されます
```
### 一括実行する場合
```bash
# 適宜ディレクトリを作成して、全ての都道府県のデータを配置します
# 離島振興対策実施地域データ: island_polygon/*_GML.zip
# 位置参照情報(街区レベル): geocoding/*.0a.zip
# 位置参照情報(大字・町丁目レベル): geocoding/*.0b.zip

# 離島振興対策実施地域データが存在する全ての都道府県の離島住所一覧を生成します
for pref_no in $(ls island_polygon | grep .zip | sed -E "s/^.+_(.*)_GML.zip/\1/"); do
  island_polygon=`ls island_polygon | grep -E "^.+_${pref_no}_GML\.zip$"`
  geocoding_block=`ls geocoding | grep -E "^${pref_no}000-.+0a\.zip$"`
  geocoding_village=`ls geocoding | grep -E "^${pref_no}000-.+0b\.zip$"`
  out_file_name=${pref_no}.csv
  if [ ! -e island_address/$out_file_name ]; then
    . ./make_island_address.sh \
        island_polygon/$island_polygon \
        geocoding/$geocoding_block \
        geocoding/$geocoding_village \
        island_address/$out_file_name
  fi
done

# 全ての都道府県の離島住所一覧を結合して1つのCSVファイル(all.csv)を生成します
awk 'FNR!=1||NR==1' island_address/??.csv > island_address/all.csv
```
