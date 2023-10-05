import os
import argparse
import logging
import csv
import pandas as pd
from tqdm.auto import tqdm
import json

parser = argparse.ArgumentParser()
parser.add_argument("--island_address", type=str, default="")
parser.add_argument("--operator", type=str, default="")
parser.add_argument("--out_file_name", type=str, default="")
parser.add_argument("--verbose", action="store_true", default=False)
args = parser.parse_args()

log_level = logging.DEBUG if args.verbose else logging.INFO
logging.basicConfig(format="[%(levelname)s] %(asctime)s: %(message)s", datefmt="%Y/%m/%d %H:%M:%S", level=log_level)
logger = logging.getLogger(__name__)

def load_csv(file_path):
    with open(file_path, encoding="utf-8", mode="r") as f:
        return [d for d in csv.DictReader(f)]

def load_excel(file_path, sheet_name="一覧", header=0, skip_row=0, skip_col=0):
    return pd.read_excel(
        file_path,
        sheet_name=sheet_name,
        index_col=None,
        header=header,
        dtype=str
    ).fillna("NULL").iloc[skip_row:, skip_col:]

def check_addresses(island_address_dicts, operator_df):
    island_addresses = set([
        e["住所"].replace(e["都道府県名"], "") for e in island_address_dicts
    ])
    checked_operator_dict = {
        "設備ID": [],
        "発電事業者名": [],
        "代表者名": [],
        "事業者の住所": [],
        "事業者の電話番号": [],
        "発電設備区分": [],
        "発電出力（kW）": [],
        "発電設備の所在地": [],
        "島内事業者": [],
        "島内発電設備": []
    }
    for a, b, c, d, e, f, g, h in tqdm(zip(
        operator_df["設備ID"],
        operator_df["発電事業者名"],
        operator_df["代表者名"],
        operator_df["事業者の住所"],
        operator_df["事業者の電話番号"],
        operator_df["発電設備区分"],
        operator_df["発電出力（kW）"],
        operator_df["発電設備の所在地"]
        ), total=len(operator_df), desc="check_island_address"):
        checked_operator_dict["設備ID"].append(a),
        checked_operator_dict["発電事業者名"].append(b),
        checked_operator_dict["代表者名"].append(c),
        checked_operator_dict["事業者の住所"].append(d),
        checked_operator_dict["事業者の電話番号"].append(e),
        checked_operator_dict["発電設備区分"].append(f),
        checked_operator_dict["発電出力（kW）"].append(g),
        checked_operator_dict["発電設備の所在地"].append(h),
        checked_operator_dict["島内事業者"].append(
            1 if any([e in d for e in island_addresses]) else 0
        ),
        checked_operator_dict["島内発電設備"].append(
            1 if any([e in h for e in island_addresses]) else 0
        )
    checked_operator_df = pd.DataFrame(checked_operator_dict)
    return checked_operator_df

def main():
    island_address_dicts = load_csv(args.island_address)
    operator_df = load_excel(args.operator, sheet_name="認定設備", header=2, skip_row=1, skip_col=1)
    checked_operator_df = check_addresses(island_address_dicts, operator_df)
    os.makedirs(os.path.dirname(args.out_file_name), exist_ok=True)
    checked_operator_df.to_csv(args.out_file_name, header=True, index=False)
    island_facility_df = checked_operator_df[
        (checked_operator_df["事業者の住所"] != "NULL")
        & (checked_operator_df["事業者の住所"] != "NULL")
        & (checked_operator_df["島内発電設備"] == 1)
    ]
    island_facility_cout = len(island_facility_df)
    pure_island_operator_df = checked_operator_df[
        (checked_operator_df["事業者の住所"] != "NULL")
        & (checked_operator_df["事業者の住所"] != "NULL")
        & (checked_operator_df["島内事業者"] == 1)
        & (checked_operator_df["島内発電設備"] == 1)
    ]
    pure_island_operator_count = len(pure_island_operator_df)
    impure_island_operator_df = checked_operator_df[
        (checked_operator_df["事業者の住所"] != "NULL")
        & (checked_operator_df["事業者の住所"] != "NULL")
        & (checked_operator_df["島内事業者"] == 0)
        & (checked_operator_df["島内発電設備"] == 1)
    ]
    impure_island_operator_count = len(impure_island_operator_df)
    stat_dict = {
        "離島住所数": len(island_address_dicts),
        "再生可能エネルギー発電設備数": len(operator_df),
        "再生可能エネルギー発電設備の割合: 発電事業者が離島内かつ発電設備の所在地が離島内 / 発電設備の所在地が離島内":
            f"{pure_island_operator_count} / {island_facility_cout} = {round(pure_island_operator_count/island_facility_cout*100, 3)}%",
        "再生可能エネルギー発電設備の割合: 発電事業者が離島外かつ発電設備の所在地が離島内 / 発電設備の所在地が離島内":
            f"{impure_island_operator_count} / {island_facility_cout} = {round(impure_island_operator_count/island_facility_cout*100, 3)}%",
    }
    logger.info(stat_dict)
    with open(f"{os.path.splitext(args.out_file_name)[0]}.json", encoding="utf-8", mode="w") as f:
        json.dump(stat_dict, f, indent=2, sort_keys=False, ensure_ascii=False)

if __name__ == "__main__":
    main()
