# !/bin/zsh

if [ "$#" -lt 1 ] 
then
    rm -rf out/*
    python3 -u src/producer_service_main.py --video_file data/traffic.mp4 --log_folder out
    python3 -u src/image_processing_service_main.py --log_folder out &
    python3 -u src/stats_reporting_service_main.py
elif [ "$1" == "1" ]
then
    rm -rf out/*
    python3 -u src/producer_service_main.py --video_file data/traffic.mp4 --log_folder out
elif [ "$1" == "2" ]
then
    python3 -u src/image_processing_service_main.py --log_folder out &
    python3 -u src/stats_reporting_service_main.py
else 
    echo "wrong argument.."
fi
