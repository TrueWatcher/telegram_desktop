#!/usr/bin/env bash
dir=$( dirname  $( readlink -f $BASH_SOURCE[0] ) )
echo "entering $dir"
cd $dir
sed "s|@dir@|$dir|g" launcher_template.txt > telegram_client.desktop
#envsubst <launcher_template.txt >telegram_client.desktop
chmod o+x telegram_client.desktop
