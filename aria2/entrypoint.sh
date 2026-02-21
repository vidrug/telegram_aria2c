#!/bin/sh
SECRET_ARG=""
if [ -n "$ARIA2_RPC_SECRET" ]; then
  SECRET_ARG="--rpc-secret=$ARIA2_RPC_SECRET"
fi
exec aria2c --conf-path=/aria2/aria2.conf $SECRET_ARG
