# Standard flow
localhost:5001/login

# Direct flow
localhost:5001/graphql
mutation {
  loginPassword(username: "ttmhuyen2110@gmail.com", password: "test") {
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



# 1) EC private key (P-256)
openssl ecparam -genkey -name prime256v1 -noout -out ec_private.pem

# 2) Self-signed cert valid 1 year
openssl req -new -x509 \
  -key ec_private.pem \
  -out ec_cert.pem \
  -days 365 \
  -subj "/CN=normal_user encryption key/"
