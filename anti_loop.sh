#!/data/data/com.termux/files/usr/bin/bash
VARIANTS=("industrial" "organic" "digital" "void" "metal" "choir")

while true; do
  V=${VARIANTS[$RANDOM % ${#VARIANTS[@]}]}
  echo "[*] new take: $V"
  python anti_variants.py --variant "$V" --duration 45

  F=$(ls -t anti_${V}_*.wav | head -1)
  ffmpeg -loglevel quiet -i "$F" -af loudnorm=I=-12:TP=-0.5 "${F%.wav}_loud.wav"
  mv "${F%.wav}_loud.wav" "${F%.wav}.wav"

  # loop it 3 times, then regenerate
  mpv --no-video --really-quiet --volume=130 --loop-file=3 "$F"

  # cleanup old (keep last 5)
  ls -t anti_${V}_*.wav | tail -n +6 | xargs -r rm
done
