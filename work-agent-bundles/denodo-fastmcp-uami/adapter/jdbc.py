"""Denodo JDBC boundary. Never put tokens in the URL or process arguments."""

import os
import re
from threading import Lock

from identity import access_token
from result_budget import bounded_result, budget_from_env


_jvm_lock = Lock()
_identifier = re.compile(r"^[a-z_][a-z0-9_]*$")


def approved_view() -> str:
    view = os.environ["DENODO_APPROVED_VIEW"]
    if not _identifier.fullmatch(view):
        raise ValueError("DENODO_APPROVED_VIEW must be one lower-case view name")
    return view


def jdbc_url() -> str:
    host = os.environ["DENODO_HOST"]
    database = os.environ["DENODO_DATABASE"]
    port = int(os.environ.get("DENODO_PORT", "9999"))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", host):
        raise ValueError("DENODO_HOST must be a DNS hostname")
    if not _identifier.fullmatch(database) or not 1 <= port <= 65535:
        raise ValueError("invalid Denodo database or port")
    return f"jdbc:denodo://{host}:{port}/{database}"


def timeout_seconds() -> int:
    value = int(os.environ.get("DENODO_QUERY_TIMEOUT_SECONDS", "5"))
    if not 1 <= value <= 30:
        raise ValueError("DENODO_QUERY_TIMEOUT_SECONDS must be 1..30")
    return value


def _java():
    import jpype

    with _jvm_lock:
        if not jpype.isJVMStarted():
            jar = os.environ.get("DENODO_JDBC_JAR", "/opt/denodo/denodo-vdp-jdbcdriver.jar")
            if not os.path.isfile(jar):
                raise RuntimeError("Denodo JDBC driver JAR is not mounted")
            jpype.startJVM(classpath=[jar], convertStrings=True)
    return jpype


def connect():
    jpype = _java()
    properties = jpype.JClass("java.util.Properties")()
    properties.setProperty("useOAuth2", "true")
    properties.setProperty("accessToken", access_token())
    properties.setProperty("ssl", "true")
    properties.setProperty("sslTrustServerCertificate", "false")
    properties.setProperty("connectTimeout", "10000")
    properties.setProperty("queryTimeout", str(timeout_seconds() * 1000))
    # Loading the driver directly avoids JVM/JDBC service-loader differences
    # when Java is embedded in Python via JPype.
    try:
        connection = jpype.JClass("com.denodo.vdp.jdbc.Driver")().connect(jdbc_url(), properties)
    except Exception:
        # Driver exceptions may echo connection properties. Never expose the
        # access token through an MCP tool error or application log.
        raise RuntimeError("DVP_JDBC_CONNECTION_FAILED") from None
    if connection is None:
        raise RuntimeError("Denodo JDBC driver did not accept the JDBC URL")
    connection.setReadOnly(True)
    return connection


def _cell(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    jpype = _java()
    if isinstance(value, jpype.JClass("java.math.BigDecimal")):
        return str(value)  # Preserve exact decimal precision.
    if isinstance(value, jpype.JClass("java.lang.Integer")) or isinstance(value, jpype.JClass("java.lang.Long")):
        return int(value)
    if isinstance(value, jpype.JClass("java.lang.Number")):
        return float(value)
    return str(value)


def query(sql_text: str, parameters: tuple[str, ...] = ()) -> dict[str, object]:
    budget = budget_from_env()
    connection = connect()
    statement = None
    result = None
    try:
        statement = connection.prepareStatement(sql_text)
        statement.setQueryTimeout(timeout_seconds())
        statement.setMaxRows(budget.max_rows + 1)
        statement.setFetchSize(budget.max_rows + 1)
        for index, value in enumerate(parameters, 1):
            statement.setString(index, value)
        result = statement.executeQuery()
        metadata = result.getMetaData()
        columns = [str(metadata.getColumnLabel(i)) for i in range(1, metadata.getColumnCount() + 1)]
        rows = []
        while len(rows) <= budget.max_rows and result.next():
            rows.append(tuple(_cell(result.getObject(i)) for i in range(1, len(columns) + 1)))
        return bounded_result(columns, rows, budget)
    finally:
        if result is not None:
            result.close()
        if statement is not None:
            statement.close()
        connection.close()
