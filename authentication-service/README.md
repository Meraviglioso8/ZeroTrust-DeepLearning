# Standard flow
localhost:5001/login

# Direct flow
localhost:5001/graphql
mutation {
  loginPassword(username: "ttmhuyen2110@gmail.com", password: "ttmhuyen2110@gmail.com") {
    accessToken
    refreshToken
    idToken
    expiresIn
  }
}

# Implicit flow
localhost:5001/graphql
query {
  implicitUrl(scope: "openid profile email")
}

# Client credentials flow
mutation {
  loginClientCredentials {
    accessToken
    expiresIn
  }
}

# Token Exchange
mutation Exchange($st: String!) {
  tokenExchange(subjectToken: $st) {
    accessToken
    refreshToken
    idToken
    expiresIn
  }
}


# Device
mutation {
  deviceAuthorize {
    deviceCode
    userCode
    verificationUri
    expiresIn
    interval
  }
}

mutation {
  refreshToken(refreshToken: "eyJhbGciOiJIUzUxMiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICI5Y2M2MGU3NS1kOWY0LTRmZjgtOTQ1OS0zYmYxNmYxZTRiYzMifQ.eyJleHAiOjE3NDY4MTEzNjEsImlhdCI6MTc0NjgxMDc2MSwianRpIjoiMzNhYjFkODMtNjZjYi00OTM4LWI5NmMtYzU4N2VjZWM2ZWM0IiwiaXNzIjoiaHR0cDovLzE3Mi4yMS4yNDAuMjA1OjMwNjQ5L3JlYWxtcy9kZXYtcmVhbG0iLCJhdWQiOiJodHRwOi8vMTcyLjIxLjI0MC4yMDU6MzA2NDkvcmVhbG1zL2Rldi1yZWFsbSIsInN1YiI6IjY5NjNlMTMyLTA0MzMtNDMwZC1hZWJhLWNmZTQ4ODA5OTUwOSIsInR5cCI6IlJlZnJlc2giLCJhenAiOiJub3JtYWxfdXNlciIsInNpZCI6Ijg4MTkyODA1LWY5ZWQtNGMxMC05Y2JkLWU4MjNiZWJjNWY2YSIsInNjb3BlIjoib3BlbmlkIGJhc2ljIHByb2ZpbGUgcm9sZXMgc2VydmljZV9hY2NvdW50IGFjciBlbWFpbCB3ZWItb3JpZ2lucyIsInJldXNlX2lkIjoiYWZjMjMzZmYtYjgxZC00ZjNjLWEwMjctYjBlMTdlNThkMWQ3In0.4u8Z8k5Csuip4MBOg-CSFE_S1iVN2bM2JKkgvx59cb8jpCpZ6FL8nXBzoG5w9Iq8Mrp-7GhTOhfLOOUKbVSwDQ") {
    accessToken
    refreshToken
    expiresIn
  }
}



# 1) EC private key (P-256)
openssl ecparam -genkey -name prime256v1 -noout -out ec_private.pem

# 2) Self-signed cert valid 1 year
openssl req -new -x509 \
  -key ec_private.pem \
  -out ec_cert.pem \
  -days 365 \
  -subj "/CN=normal_user encryption key/"
