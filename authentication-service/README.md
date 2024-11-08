# Authentication API references

```
http://localhost:5001/authentication
```

## 1. Sign Up

![Sign Up API](./images/signup.png)

```graphQL

mutation Signup($email: String!, $password: String!) {
  signup(email: $email, password: $password) {
    info
    qrCode
  }
}

{
  "email": "newcustomer@example.com",
  "password": "CustomerPass123"
}


```
### 1.1 Pre-share key QR

![QR](./images/qr.png)

## 2. Sign In

![Sign In API](./images/signin.png)

```graphQL

mutation Login($email: String!, $password: String!, $totpCode: String!) {
  login(email: $email, password: $password, totpCode: $totpCode) {
    info
    token
  }
}

{
  "email": "newcustomer@example.com",
  "password": "CustomerPass123",
  "totpCode": "510118"
}


```
