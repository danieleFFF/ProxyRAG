import base64
import json
import os
import sys
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from keycloak import KeycloakOpenID
from keycloak.exceptions import KeycloakError

class KeycloakUser:
    def __init__(self, user_info, roles):
        self.username = user_info.get('preferred_username', '')
        self.email = user_info.get('email', '')
        self.roles = roles
        self.is_authenticated = True

    @property # the user isn't anonymous
    def is_anonymous(self):
        return False

# jwt token's structure is header+payload+signature: 
# the payload contains user's data and roles in Keycloak and is encoded with base64url

# this function decodes the base64 string into json text and then into python dictionary {"realm_access":{"roles":["user"]}}, to then extract user's roles
def decode_jwt_payload(token):
    try:
        parts = token.split('.')
        if len(parts) == 3:
            payload_b64 = parts[1] + '=' * (4 - len(parts[1]) % 4)
            return json.loads(base64.urlsafe_b64decode(payload_b64).decode('utf-8'))
    except Exception:
        pass

    return {}

# inherits directly from drf class "BaseAuthentication"
class KeycloakAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.lower().startswith('bearer '): # if token is Bearer
            raise AuthenticationFailed('Token Bearer missing.')

        token = auth_header.split()[1] #real token value

        # Openwebui sends calls with "dummy" token
        if token == os.getenv('OPENAI_API_KEY', 'dummy'):
            # the proxy intercepts the  "Email" and "Name" headers 
            email = request.headers.get('X-Openwebui-User-Email') #reads only the user's email in the headers
            
            if email:
                # the user "system" is used as bypass for the proxy to get the models, otherwise it would return 403 when openwebui does background calls (polling)
                user_info = {
                    "preferred_username": request.headers.get('X-Openwebui-User-Name', 'system'),
                    "email": email,
                }

                roles = [request.headers.get('X-Openwebui-User-Role', 'user')] #reads only the user's role in the headers
                
                # retrieves the Keycloak OIDC/userinfo URLs from settings to determine the realm and server url
                userinfo_url = getattr(settings, 'KEYCLOAK_USERINFO_URL', 'http://keycloak:8080/realms/openwebui-realm/protocol/openid-connect/userinfo')
                if '/realms/' in userinfo_url:
                    server_url = userinfo_url.split('/realms/')[0] + '/'
                    realm_name = userinfo_url.split('/realms/')[1].split('/')[0]
                else:
                    server_url = 'http://keycloak:8080/'
                    realm_name = 'openwebui-realm'

                admin_password = os.getenv('KEYCLOAK_ADMIN_PASSWORD')
                if admin_password:
                    admin_password = admin_password.strip()
                    admin_username = os.getenv('KEYCLOAK_ADMIN', 'admin').strip()
                    try:
                        from keycloak import KeycloakAdmin
                        keycloak_admin = KeycloakAdmin(
                            server_url=server_url,
                            username=admin_username,
                            password=admin_password,
                            realm_name=realm_name,
                            user_realm_name='master',
                            verify=False
                        )
                        
                        # fetches the user by email
                        users = keycloak_admin.get_users({"email": email})
                        
                        if users:
                            user_id = users[0]['id']
                            # Get realm roles
                            realm_roles = keycloak_admin.get_realm_roles_of_user(user_id=user_id)
                            roles.extend([r['name'] for r in realm_roles if isinstance(r, dict) and 'name' in r])
                            
                            # gets client roles for openwebui
                            try:
                                internal_client_id = keycloak_admin.get_client_id("openwebui")
                                
                                if internal_client_id:
                                    client_roles = keycloak_admin.get_client_roles_of_user(user_id=user_id, client_id=internal_client_id)
                                    roles.extend([r['name'] for r in client_roles if isinstance(r, dict) and 'name' in r])
                            except Exception as client_err:
                                sys.stderr.write(f"KeycloakAdmin client roles error: {str(client_err)}\n")
                                sys.stderr.flush()
                                
                    except Exception as admin_err:
                        sys.stderr.write(f"KeycloakAdmin error: {str(admin_err)} (user={repr(admin_username)}, pwd={repr(admin_password)}, url={repr(server_url)}, realm={repr(realm_name)})\n")
                        sys.stderr.flush()

                # cleans up and deduplicate roles list
                roles = list(set(roles))
                
                return (KeycloakUser(user_info, roles), token)
            
            # automatic background call from openwebui to register the models: system can see all the models
            return (KeycloakUser({"preferred_username": "system", "email": "system@local"}, ["system"]), token)

        # token JWT validation management with Keycloak + python-keycloak (used when clients call for proxy)
        # it contacts /userinfo to extract the roles
        userinfo_url = getattr(settings, 'KEYCLOAK_USERINFO_URL', 'http://keycloak:8080/realms/openwebui-realm/protocol/openid-connect/userinfo')
        
        if '/realms/' in userinfo_url:
            server_url = userinfo_url.split('/realms/')[0] + '/'
            realm_name = userinfo_url.split('/realms/')[1].split('/')[0]
        else:
            server_url = 'http://keycloak:8080/'
            realm_name = 'openwebui-realm'

        # call that validates the token and takes user info from keycloak's server
        keycloak_openid = KeycloakOpenID(
            server_url=server_url,
            client_id="openwebui",
            realm_name=realm_name
        )

        try:
            user_info = keycloak_openid.userinfo(token)
        except KeycloakError as e:
            raise AuthenticationFailed(f'Keycloak error: {str(e)}')

        decoded = decode_jwt_payload(token)
        
        # extracts realm roles
        roles = decoded.get('realm_access', {}).get('roles', [])
        
        # extracts all client roles from resource_access
        resource_access = decoded.get('resource_access', {})
        
        for client_id, client_data in resource_access.items():
            client_roles = client_data.get('roles', [])
            roles.extend(client_roles)

        return (KeycloakUser(user_info, roles), token)
