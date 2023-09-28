import os
import argparse
import logging
import shutil
import glob
import json
import csv
import dask
dask.config.set(scheduler="processes")
import dask.bag as db
from dask.diagnostics import ProgressBar
import kanjize
import mojimoji
from shapely import geometry

parser = argparse.ArgumentParser()
parser.add_argument("--island_polygon", type=str, default="")
parser.add_argument("--geocoding_block", type=str, default="")
parser.add_argument("--geocoding_village", type=str, default="")
parser.add_argument("--out_file_name", type=str, default="")
parser.add_argument("--specific_area", type=str, default="")
parser.add_argument("--verbose", action="store_true", default=False)
args = parser.parse_args()

log_level = logging.DEBUG if args.verbose else logging.INFO
logging.basicConfig(format="[%(levelname)s] %(asctime)s: %(message)s", datefmt="%Y/%m/%d %H:%M:%S", level=log_level)
logger = logging.getLogger(__name__)

def unpack(file_path, file_name="*.csv"):
    dir_name = os.path.splitext(file_path)[0]
    if not os.path.isdir(dir_name):
        shutil.unpack_archive(file_path, os.path.dirname(file_path))
    return [f for f in glob.glob(f"{dir_name}/{file_name}")]

def load_island_polygon():
    file = unpack(file_path=args.island_polygon, file_name="*.geojson")[0]
    with open(file, encoding="utf-8", mode="r") as f:
        island_polygon_raw_dict = json.load(f)
    island_latlon_dicts = []
    for feature in island_polygon_raw_dict["features"]:
        island_latlon_dict = {
            "離島ID": feature["properties"]["A19_001"],
            "行政区域コード": feature["properties"]["A19_002"],
            "都道府県名": feature["properties"]["A19_003"],
            "支庁・振興局名": feature["properties"]["A19_004"],
            "郡・政令都市名": feature["properties"]["A19_005"],
            "市区町村名": feature["properties"]["A19_006"],
            "原典市区町村名": feature["properties"]["A19_007"],
            "指定地域名": feature["properties"]["A19_008"],
            "島名": feature["properties"]["A19_009"],
            "coordinates": feature["geometry"]["coordinates"][0]
        }
        island_latlon_dicts.append(island_latlon_dict)
    return island_latlon_dicts

def load_geocoding_block():
    file = unpack(file_path=args.geocoding_block, file_name="*.csv")[0]
    with open(file, encoding="shift_jis", mode="r") as f:
        geocoding_block_raw_dicts = [d for d in csv.DictReader(f)]
    geocoding_block_dicts = []
    for d in geocoding_block_raw_dicts:
        geocoding_block_dict = {
            "レベル": "街区",
            "都道府県名": d["都道府県名"],
            "市区町村名": d["市区町村名"],
            "大字・丁目名": d["大字・丁目名"],
            "小字・通称名": d["小字・通称名"],
            "街区符号・地番": d["街区符号・地番"],
            "coordinate": [float(d["経度"]), float(d["緯度"])]
        }
        geocoding_block_dicts.append(geocoding_block_dict)
    return geocoding_block_dicts

def load_geocoding_village():
    file = unpack(file_path=args.geocoding_village, file_name="*.csv")[0]
    with open(file, encoding="shift_jis", mode="r") as f:
        geocoding_village_raw_dicts = [d for d in csv.DictReader(f)]
    geocoding_village_dicts = []
    for d in geocoding_village_raw_dicts:
        geocoding_village_dict = {
            "レベル": "大字",
            "都道府県名": d["都道府県名"],
            "市区町村名": d["市区町村名"],
            "大字・丁目名": d["大字町丁目名"],
            "小字・通称名": "",
            "街区符号・地番": "",
            "coordinate": [float(d["経度"]), float(d["緯度"])]
        }
        geocoding_village_dicts.append(geocoding_village_dict)
    return geocoding_village_dicts

kanji_addresses = [(f"{kanjize.number2kanji(i)}丁目", f"{i}-") for i in range(100)]
kanji_addresses += [(f"{kanjize.number2kanji(i)}番地", f"{i}-") for i in range(100)]
kanji_addresses += [(f"{kanjize.number2kanji(i)}号", f"{i}") for i in range(100)]
def normalize_address(address="三尾野三丁目二番地一号"):
    normalized_address = address
    for kanji_address in kanji_addresses:
        normalized_address = normalized_address.replace(kanji_address[0], kanji_address[1])
    normalized_address = normalized_address[:-1] if normalized_address.endswith("-") else normalized_address
    normalized_address = mojimoji.han_to_zen(normalized_address, kana=True, digit=True, ascii=True)
    return normalized_address

def fillna(e):
    return str(e) if e is not None else ""

def check_island(island_latlon_dicts, geocoding_block_dicts, geocoding_village_dicts):
    logger.info(f"離島ポリゴンデータ数: {len(island_latlon_dicts)}")
    geocoding_dicts = geocoding_block_dicts + geocoding_village_dicts
    logger.info(f"ジオコーディングデータ数: {len(geocoding_dicts)}")
    filtered_geocoding_dicts = [
        geocoding_dict
        for geocoding_dict in geocoding_dicts
        if geocoding_dict["市区町村名"] in set(
            island_latlon_dict["市区町村名"]
            for island_latlon_dict in island_latlon_dicts
        )
    ]
    logger.info(f"離島候補_ジオコーディングデータ数: {len(filtered_geocoding_dicts)}")
    geocoding_dict_db = db.from_sequence(filtered_geocoding_dicts, npartitions=5000)
    def udf_check_island(geocoding_dict):
        checked_island_dict = {}
        point = geometry.Point(geocoding_dict["coordinate"][0], geocoding_dict["coordinate"][1])
        for island_latlon_dict in island_latlon_dicts:
            polygon = geometry.Polygon(island_latlon_dict["coordinates"])
            if polygon.contains(point):
                checked_island_dict["レベル"] = fillna(geocoding_dict["レベル"])
                checked_island_dict["都道府県名"] = fillna(geocoding_dict["都道府県名"])
                checked_island_dict["市区町村名"] = fillna(geocoding_dict["市区町村名"])
                checked_island_dict["大字・丁目名"] = fillna(geocoding_dict["大字・丁目名"])
                checked_island_dict["小字・通称名"] = fillna(geocoding_dict["小字・通称名"])
                checked_island_dict["街区符号・地番"] = fillna(geocoding_dict["街区符号・地番"])
                checked_island_dict["離島ID"] = fillna(island_latlon_dict["離島ID"])
                checked_island_dict["行政区域コード"] = fillna(island_latlon_dict["行政区域コード"])
                checked_island_dict["支庁・振興局名"] = fillna(island_latlon_dict["支庁・振興局名"])
                checked_island_dict["郡・政令都市名"] = fillna(island_latlon_dict["郡・政令都市名"])
                checked_island_dict["原典市区町村名"] = fillna(island_latlon_dict["原典市区町村名"])
                checked_island_dict["指定地域名"] = fillna(island_latlon_dict["指定地域名"])
                checked_island_dict["島名"] = fillna(island_latlon_dict["島名"])
                checked_island_dict["住所"] = normalize_address(
                    checked_island_dict["都道府県名"]
                    + checked_island_dict["市区町村名"]
                    + checked_island_dict["大字・丁目名"]
                    + checked_island_dict["小字・通称名"]
                    + checked_island_dict["街区符号・地番"]
                )
                break
        return checked_island_dict
    with ProgressBar():
        _checked_island_dicts = geocoding_dict_db.map(udf_check_island).compute()
    checked_island_dicts = [e for e in _checked_island_dicts if len(e) > 0]
    logger.info(f"離島住所数: {len(checked_island_dicts)}")
    return checked_island_dicts

def save(checked_island_dicts):
    os.makedirs(os.path.dirname(args.out_file_name), exist_ok=True)
    with open(args.out_file_name, encoding="utf-8", mode="w") as f:
        writer = csv.DictWriter(f, list(checked_island_dicts[0].keys()))
        writer.writeheader()
        writer.writerows(checked_island_dicts)
    logger.info(f"Saved: {args.out_file_name}")

def main():
    island_latlon_dicts = load_island_polygon()
    geocoding_block_dicts = load_geocoding_block()
    geocoding_village_dicts = load_geocoding_village()
    if args.specific_area:
        island_latlon_dicts = [e for e in island_latlon_dicts if e["市区町村名"] == args.specific_area]
        geocoding_block_dicts = [e for e in geocoding_block_dicts if e["市区町村名"] == args.specific_area]
        geocoding_village_dicts = [e for e in geocoding_village_dicts if e["市区町村名"] == args.specific_area]
    checked_island_dicts = check_island(island_latlon_dicts, geocoding_block_dicts, geocoding_village_dicts)
    save(checked_island_dicts)

if __name__ == '__main__':
    main()
