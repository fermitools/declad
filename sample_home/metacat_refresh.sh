
. $HOME/packages/setup-env.sh
spack load --first metacat

# environment vars to talk to metacat
export METACAT_SERVER_URL=https://metacat.xxxx.yyy:9443/hypot_meta_prod/app
export METACAT_AUTH_SERVER_URL=https://metacat.xxxx.yyy:8143/auth/hypot

# get grid proxy for file transfers(?)
grid-proxy-init -cert $HOME/certs/hypot-declad.xxxx.yyy-cert.pem -key $HOME/certs/hypot-declad.xxxx.yyy-key.pem

# refresh token for file transfers
export HTGETTOKENOPTS="--credkey=hypotpro/managedtokens/fifeutilgpvm01.xxxx.yyy"
htgettoken -i hypot -r production -a htvaultprod.xxxx.yyy

# refresh metacat authentication
metacat auth login -m x509 -c $HOME/certs/hypot-declad.xxxx.yyy-cert.pem -k $HOME/certs/hypot-declad.xxxx.yyy-key.pem hypotpro
# metacat auth login -m token hypotpro

