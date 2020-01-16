#!/usr/bin/env bash

./manage.py migrate --noinput
pushd var/conf/extra_locale; ../../../manage.py compilemessages; popd
./manage.py collectstatic --clear --noinput --verbosity=0
./manage.py sync_translation_fields --noinput
./manage.py update_translation_fields
./manage.py update_geotrek_permissions
rm -rf var/tmp/*
