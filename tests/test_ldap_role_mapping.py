"""
LDAP 组映射角色测试：LDAP_ROLE_ATTRIBUTE + LDAP_ROLE_MAPPING 的解析与匹配。

映射格式（分号分隔条目，DN 含逗号故不用逗号）：
  cn=gengfu-admins,ou=groups,dc=x=Admin;cn=gengfu-users,ou=groups,dc=x=User
"""

from keep.identitymanager.identity_managers.ldap.ldap_identitymanager import (
    LdapIdentityManager,
)


from types import SimpleNamespace


def _entry_with(members=None, single=None):
    """构造用户对象桩：属性返回值列表或标量（贴近 ldap3 Attribute 语义）。"""
    attrs = {}
    if members is not None:
        attrs["memberOf"] = SimpleNamespace(values=members if isinstance(members, list) else [members])
    for k, v in (single or {}).items():
        attrs[k] = SimpleNamespace(values=v if isinstance(v, list) else [v])
    return SimpleNamespace(**attrs)


def _manager(role_mapping="", default_role="Admin", role_attribute="memberOf"):
    m = LdapIdentityManager.__new__(LdapIdentityManager)
    m.ldap_default_role = default_role
    m.ldap_role_attribute = role_attribute
    m.ldap_role_mapping = LdapIdentityManager._parse_role_mapping(role_mapping)
    m.ldap_configured = True
    return m


def _entry(member_of):
    return _entry_with(members=member_of)


class TestParseRoleMapping:
    def test_parse_semicolon_entries(self):
        m = _manager("cn=a,dc=x=Admin;cn=b,dc=x=User")
        assert m.ldap_role_mapping == [("cn=a,dc=x", "Admin"), ("cn=b,dc=x", "User")]

    def test_empty_mapping(self):
        assert _manager("").ldap_role_mapping == []

    def test_ignores_malformed_entry(self):
        m = _manager("no-equals-here;cn=a,dc=x=Admin")
        assert m.ldap_role_mapping == [("cn=a,dc=x", "Admin")]


class TestResolveRole:
    def test_no_mapping_falls_back_to_default(self):
        m = _manager(role_mapping="")
        assert m._resolve_role(_entry(["cn=whatever"])) == "admin"

    def test_exact_dn_match(self):
        m = _manager("cn=gengfu-admins,ou=groups,dc=gengfu,dc=test=Admin;cn=gengfu-users,ou=groups,dc=gengfu,dc=test=User")
        entry = _entry(["cn=gengfu-users,ou=groups,dc=gengfu,dc=test"])
        assert m._resolve_role(entry) == "user"

    def test_suffix_match_on_group_name(self):
        """运维只写组名也能匹配 DN 尾部。"""
        m = _manager("gengfu-admins=Admin")
        entry = _entry(["cn=gengfu-admins,ou=groups,dc=gengfu,dc=test"])
        assert m._resolve_role(entry) == "admin"

    def test_no_match_falls_back_to_default(self):
        m = _manager("gengfu-admins=Admin", default_role="User")
        entry = _entry(["cn=other-group"])
        assert m._resolve_role(entry) == "user"

    def test_first_matching_entry_wins(self):
        m = _manager("gengfu-admins=Admin;gengfu-users=User")
        entry = _entry(["cn=gengfu-users,ou=groups", "cn=gengfu-admins,ou=groups"])
        # 映射表顺序优先：先声明的 Admin 命中
        assert m._resolve_role(entry) == "admin"

    def test_missing_attribute_falls_back_to_default(self):
        m = _manager("gengfu-admins=Admin")
        entry = _entry_with()  # 无 memberOf
        assert m._resolve_role(entry) == "admin"

    def test_custom_role_attribute(self):
        m = _manager("engineer=User", role_attribute="employeeType")
        entry = _entry_with(single={"employeeType": ["engineer"]})
        assert m._resolve_role(entry) == "user"
