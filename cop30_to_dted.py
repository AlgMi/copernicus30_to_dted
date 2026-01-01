import os
import subprocess
import boto3
import argparse
from datetime import datetime
from botocore import UNSIGNED
from botocore.config import Config

def get_dted_level2_width(lat):
    #Returns mandatory DTED Level 2 width based on MIL-PRF-89020B
    abs_lat = abs(lat)
    if abs_lat < 50: return 3601
    elif abs_lat < 70: return 1801
    elif abs_lat < 75: return 1201
    elif abs_lat < 80: return 901
    else: return 601

def get_tile_name(lat, lon):
    ns = 'N' if lat >= 0 else 'S'
    ew = 'E' if lon >= 0 else 'W'
    return f"Copernicus_DSM_COG_10_{ns}{abs(lat):02}_00_{ew}{abs(lon):03}_00_DEM"

def download_tile(tile_name):
    s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))
    key = f"{tile_name}/{tile_name}.tif"
    local_file = f"{tile_name}.tif"
    
    if os.path.exists(local_file):
        print(f"[INFO] File {local_file} already exists. Skipping download.")
        return local_file
    
    try:
        print(f"[INFO] Downloading {tile_name} from AWS...")
        s3.download_file('copernicus-dem-30m', key, local_file)
        return local_file
    except Exception as e:
        print(f"[ERROR] Failed to download {tile_name}: {e}")
        return None

def process_to_dted(tif_file, lat, lon, output_base):
    width = get_dted_level2_width(lat)
    height = 3601 
    
    ew_dir = f"e{abs(lon):03}"
    ns_file = f"n{abs(lat):02}.dt2"
    target_dir = os.path.join(output_base, ew_dir)
    os.makedirs(target_dir, exist_ok=True)
    final_path = os.path.join(target_dir, ns_file)

    temp_stage1 = f"temp_{lat}_{lon}_1.tif"
    temp_stage2 = f"temp_{lat}_{lon}_2.tif"

    try:
        subprocess.run([
            'gdal_translate', '-of', 'GTiff', '-q',
            '-projwin', str(float(lon)), str(float(lat + 1)), str(float(lon + 1)), str(float(lat)),
            '-outsize', str(width), str(height),
            '-a_nodata', '-9999', # Hack to fix missing pixel removed for cloud optimization.
            tif_file, temp_stage1
        ], check=True)

        subprocess.run(['gdal_fillnodata.py', '--config', 'GDAL_PAM_ENABLED', 'NO', '-q', '-md', '2', temp_stage1, temp_stage2], check=True)

        subprocess.run(['gdal_translate', '--config', 'GDAL_PAM_ENABLED', 'NO', '-of', 'DTED', '-q', '-co', 'LEVEL=2', temp_stage2, final_path], check=True)
        return True
    except Exception as e:
        print(f"[ERROR] Error processing {tif_file}: {e}")
        return False
    finally:
        for f in [temp_stage1, temp_stage2]:
            if os.path.exists(f): os.remove(f)

def main():
    parser = argparse.ArgumentParser(description="Download Copernicus DEM and convert to DTED Level 2")
    
    # Latitude Arguments
    parser.add_argument("--lat_min", type=int, default=53, help="Minimum Latitude (inclusive)")
    parser.add_argument("--lat_max", type=int, default=57, help="Maximum Latitude (exclusive)")
    
    # Longitude Arguments
    parser.add_argument("--lon_min", type=int, default=20, help="Minimum Longitude (inclusive)")
    parser.add_argument("--lon_max", type=int, default=28, help="Maximum Longitude (exclusive)")
    
    # Output Directory
    parser.add_argument("--output", type=str, default="./DTED_Lithuania", help="Base output directory")

    args = parser.parse_args()

    start_time = datetime.now()
    print(f"--- Process Started at {start_time.strftime('%Y-%m-%d %H:%M:%S')} ---")
    print(f"Coverage: Lat {args.lat_min}-{args.lat_max}, Lon {args.lon_min}-{args.lon_max}")
    print(f"Target directory: {args.output}")

    success_count = 0
    fail_count = 0

    for lat in range(args.lat_min, args.lat_max):
        for lon in range(args.lon_min, args.lon_max):
            tile_name = get_tile_name(lat, lon)
            tif_file = download_tile(tile_name)
            
            if tif_file and process_to_dted(tif_file, lat, lon, args.output):
                success_count += 1
                if os.path.exists(tif_file): os.remove(tif_file)
            else:
                fail_count += 1

    print(f"\n--- Process Complete. Success: {success_count}, Fail: {fail_count} ---")

if __name__ == "__main__":
    main()