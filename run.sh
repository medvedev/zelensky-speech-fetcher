#!/bin/bash

if [ "$(git diff --name-only --exit-code origin/main -- last_speech_timestamp_ua.txt)" ]; then
  echo "CHANGES in last_speech_timestamp.txt"
else
  echo "No changes in last_speech_timestamp.txt"
fi
