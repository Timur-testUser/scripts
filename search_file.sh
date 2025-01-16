#!/bin/bash

# Поиск файла в директориях
echo "Введите имя файла:"
read file_name
echo "Введите директории, в которых вы хотите искать файл
(например, /home/user /usr/local/bin):"
read directories

# Поиск файла в директориях
echo "Поиск файла..."
for dir in $directories
do
  if [ -f "$dir/$file_name" ]
  then
    echo "Файл найден в директории $dir"
    exit 0
  fi
done
echo "Файл $file_name не найден в заданных директориях."
