cmd=$1
num=$2

run_in_docker() {
    local command=$1
    local app_dir=$(pwd)

    docker run -it --rm \
        -v "$app_dir:/app" \
        jodi-control \
        /bin/bash -c "cd /app && $command"
}

case "$cmd" in
  run)
    case "$num" in
      1)
        run_in_docker "python jodi/prototype/experiments/scalability.py --experiment 1"
        ;;
      2)
        run_in_docker "python jodi/prototype/experiments/microbenchmark.py"
        ;;
      3)
        ./scripts/runk6.sh
        ;;
      *)
        echo "Invalid experiment number. Allowed values are: {1|2|3}"
        exit 1
        ;;
    esac
    ;;
  *)
    echo "Usage: $0 {run} {1|2|3}"
    exit 1
    ;;
esac