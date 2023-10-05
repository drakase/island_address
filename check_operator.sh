export VIRTUAL_ENV="VENV"
export PYTHONPATH=$VIRTUAL_ENV
export PATH="$VIRTUAL_ENV/bin:$PATH"

python check_operator.py \
    --island_address $1 \
    --operator $2 \
    --out_file_name $3
