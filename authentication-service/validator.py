from marshmallow import Schema, fields, validate

REGEX_EMAIL = r'^(([^<>()[\]\.,;:\s@\"]+(\.[^<>()[\]\.,;:\s@\"]+)*)|(\".+\"))@(([^<>()[\]\.,;:\s@\"]+\.)+[^<>()[\]\.,' \
              r';:\s@\"]{2,})$'
REGEX_VALID_PASSWORD = r'^(?=.*[0-9])(?=.*[a-zA-Z])(?!.* ).{8,16}$'

class LoginBodyValidation(Schema):
    email = fields.String(required=True, validate=[validate.Length(min=1, max=50), validate.Regexp(REGEX_EMAIL)])
    password = fields.String(required=True,
                             validate=[validate.Length(min=1, max=16), validate.Regexp(REGEX_VALID_PASSWORD)])


class SignupBodyValidation(Schema):
    email = fields.String(required=True, validate=[validate.Length(min=1, max=50), validate.Regexp(REGEX_EMAIL)])
    password = fields.String(required=True,
                             validate=[validate.Length(min=1, max=16), validate.Regexp(REGEX_VALID_PASSWORD)])



