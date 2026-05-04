> 注册登录-链路


注册
```text
client -> gateway /api/v1/auth/register
gateway -> auth-service /api/v1/auth/register
auth-service -> user-service 创建用户
auth-service -> 绑定密码
```


登录
```text
client -> gateway /api/v1/auth/login
gateway -> auth-service /api/v1/auth/login
auth-service -> 校验用户名密码
auth-service -> 签发 access_token / refresh_token
```


访问当前用户
```text
client -> gateway /api/v1/users/me + Bearer token
gateway 校验 JWT
gateway 注入 X-User-ID + X-Internal-Token
gateway -> user-service /api/v1/users/me
user-service 返回当前用户资料
```


刷新 token
```text
client -> gateway /api/v1/auth/refresh + Bearer refresh_token
gateway -> auth-service /api/v1/auth/refresh
auth-service -> 校验 refresh_token 有效性
auth-service -> 签发新的 access_token / refresh_token
```
