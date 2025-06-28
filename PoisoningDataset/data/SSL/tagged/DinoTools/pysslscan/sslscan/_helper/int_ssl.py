import flextls
import ssl

def convert_version2method(protocol_version):
    """
    Convert internal protocol version ID to Python SSL method.

    :param Integer protocol_version: Version ID
    :return: OpenSSL method or None if not found
    :rtype: OpenSSL method or None
    """
    if protocol_version == flextls.registry.version.SSLv2:
<target>
        return ssl.PROTOCOL_SSLv2
</target>
    if protocol_version == flextls.registry.version.SSLv3:
<target>
        return ssl.PROTOCOL_SSLv3
</target>
    if protocol_version == flextls.registry.version.TLSv10:
<target>
        return ssl.PROTOCOL_TLSv1
</target>
    if protocol_version == flextls.registry.version.TLSv11:
<target>
        return ssl.PROTOCOL_TLSv1_1
</target>
    if protocol_version == flextls.registry.version.TLSv12:
<target>
        return ssl.PROTOCOL_TLSv1_2
</target>

    return None

def convert_versions2methods(protocol_versions):
    """
    Convert list of internal protocol versions to Python SSL methods. 
    :param List protocol_version: List of internal protocol version IDs
    :return: List of methods
    :rtype: List
    """

    methods = []
    for protocol_version in protocol_versions:
        method = convert_version2method(protocol_version)
        if method in methods:
            continue
        if method is not None:
            methods.append(method)

    return methods