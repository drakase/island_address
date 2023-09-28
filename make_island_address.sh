export VIRTUAL_ENV="VENV"
export PYTHONPATH=$VIRTUAL_ENV
export PATH="$VIRTUAL_ENV/bin:$PATH"

python make_island_address.py \
    --island_polygon $1 \
    --geocoding_block $2 \
    --geocoding_village $3 \
    --out_file_name $4
