# Simple
# ffmpeg -f image2 -framerate 2 -start_number 1 -i '%d.png' -vf smartblur=ls=0.5 ledscreen.gif

# Really cool "decimated voxel-font" effect
# ffmpeg -framerate 2 -start_number 1 -i '%d.png' -vf palettegen=4 palette.png
# ffmpeg -framerate 2 -start_number 1 -i '%d.png' -i palette.png -filter_complex "fps=20,scale=720:-1:flags=lanczos[x];[x][1:v]paletteuse" ledscreen.gif

# Crispy clean GIF
ffmpeg -hide_banner -loglevel error -framerate 60 -start_number 1 -i '%d.png' -vf "scale=54:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" -loop 0 -y ledscreen.gif
