# Authorization API references

```
http://localhost:5002/authorization
```

## 1. Add Permissions

![Sign Up API](./images/add.png)

```graphQL

mutation AddPermissions($userId: String!, $permissions: [String!]!) {
    addPermission(userId: $userId, permissions: $permissions) {
        info
        permissions
    }
}

{
    "userId": "13",
    "permissions": ["view_orders"]
}


```

## 2. Change Permissions

![Sign In API](./images/change.png)

```graphQL

mutation ChangePermissions($userId: String!, $newPermissions: [String!]!) {
    changePermissions(userId: $userId, newPermissions: $newPermissions) {
        info
        permissions
    }
}

{
    "userId": "13",
    "newPermissions": ["hehe", "process_orders"]
}


```

## 3. Remove Permissions

![Sign In API](./images/remove.png)

```graphQL

mutation RemovePermissions($userId: String!, $permissions: [String!]!) {
    removePermissions(userId: $userId, permissions: $permissions) {
        info
        permissions
    }
}

{
    "userId": "13",
    "permissions": ["hehe"]
}

```
