#!/bin/bash

# Проверяем, передан ли аргумент
if [ -z "$1" ]; then
    echo "Usage: $0 <path_to_source_png>"
    exit 1
fi

SOURCE_FILE="$1"
FILENAME=$(basename -- "$SOURCE_FILE")
EXTENSION="${FILENAME##*.}"
BASENAME="${FILENAME%.*}"

# Проверяем, является ли файл PNG
if [ "$EXTENSION" != "png" ]; then
    echo "Error: Source file must be a PNG image."
    exit 1
fi

# Создаем временную директорию для иконок macOS
ICONSET_DIR="${BASENAME}.iconset"
mkdir -p "$ICONSET_DIR"

# Определяем список нужных размеров
SIZES=(16 32 64 128 256 512 1024)

# Генерируем PNG-иконки для macOS (.icns)
echo "Generating macOS icon sizes..."
# Перенаправляем вывод ошибок (2>) в /dev/null
for size in "${SIZES[@]}"; do
    magick convert "$SOURCE_FILE" -resize "${size}x${size}" "$ICONSET_DIR/icon_${size}x${size}.png" 2>/dev/null
    magick convert "$SOURCE_FILE" -resize "$((size*2))x$((size*2))" "$ICONSET_DIR/icon_${size}x${size}@2x.png" 2>/dev/null
done

# Генерируем файл .icns из папки iconset
echo "Creating .icns file..."
iconutil -c icns "$ICONSET_DIR" -o "${BASENAME}.icns"

# Очищаем временную директорию
echo "Cleaning up..."
rm -r "$ICONSET_DIR"

# Генерируем файл .ico для Windows
echo "Generating .ico file..."
magick convert "$SOURCE_FILE" -resize 16x16 \
        -resize 32x32 \
        -resize 48x48 \
        -resize 64x64 \
        -resize 256x256 \
        "${BASENAME}.ico" 2>/dev/null
        
echo "Done! Generated ${BASENAME}.icns and ${BASENAME}.ico"