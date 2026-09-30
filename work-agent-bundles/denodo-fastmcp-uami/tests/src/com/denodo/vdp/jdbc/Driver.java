package com.denodo.vdp.jdbc;

import java.lang.reflect.Proxy;
import java.sql.*;
import java.util.Properties;
import java.util.logging.Logger;

/** Synthetic test driver. Never ship this JAR in the deployment image. */
public final class Driver implements java.sql.Driver {
    public Connection connect(String url, Properties props) throws SQLException {
        if (!url.equals("jdbc:denodo://denodo.example.invalid:9999/synthetic")
                || !"true".equals(props.getProperty("useOAuth2"))
                || !"lab-token".equals(props.getProperty("accessToken"))
                || !"true".equals(props.getProperty("ssl"))
                || !"false".equals(props.getProperty("sslTrustServerCertificate"))
                || !"10000".equals(props.getProperty("connectTimeout"))
                || !"5000".equals(props.getProperty("queryTimeout"))) {
            throw new SQLException("LAB_JDBC_PROPERTIES_REJECTED");
        }
        final boolean[] readOnly = {false};
        return (Connection) Proxy.newProxyInstance(getClass().getClassLoader(), new Class[]{Connection.class},
            (proxy, method, args) -> {
                switch (method.getName()) {
                    case "setReadOnly": readOnly[0] = (Boolean) args[0]; return null;
                    case "prepareStatement":
                        if (!readOnly[0]) throw new SQLException("LAB_NOT_READ_ONLY");
                        return statement((String) args[0]);
                    case "close": return null;
                    case "isClosed": return false;
                    default: throw new SQLFeatureNotSupportedException(method.getName());
                }
            });
    }

    private PreparedStatement statement(String sql) {
        final String[] parameter = {null};
        final int[] timeout = {0};
        final int[] maxRows = {0};
        return (PreparedStatement) Proxy.newProxyInstance(getClass().getClassLoader(), new Class[]{PreparedStatement.class},
            (proxy, method, args) -> {
                switch (method.getName()) {
                    case "setQueryTimeout": timeout[0] = (Integer) args[0]; return null;
                    case "setMaxRows": maxRows[0] = (Integer) args[0]; return null;
                    case "setFetchSize": return null;
                    case "setString": parameter[0] = (String) args[1]; return null;
                    case "executeQuery":
                        if (timeout[0] < 1 || timeout[0] > 30 || maxRows[0] != 51)
                            throw new SQLException("LAB_BOUNDS_REJECTED");
                        if (sql.equals("SELECT 1"))
                            return result(new String[]{"1"}, new Object[][]{{1}});
                        if (sql.contains("COUNT(DISTINCT namespace_name)") && sql.contains("approved_namespace_inventory"))
                            return result(new String[]{"namespace_count"}, new Object[][]{{3}});
                        if (sql.contains("WHERE namespace_name = ?") && sql.contains("approved_namespace_inventory"))
                            return result(new String[]{"namespace_name", "owner_team", "workload_type", "lob", "region", "workload_count", "running_pod_count", "observed_at"},
                                "payments".equals(parameter[0]) ? new Object[][]{{"payments", "team-a", "Deployment", "demo", "lab", 2, 3, "synthetic"}} : new Object[][]{});
                        throw new SQLException("LAB_QUERY_REJECTED");
                    case "close": return null;
                    default: throw new SQLFeatureNotSupportedException(method.getName());
                }
            });
    }

    private ResultSet result(String[] columns, Object[][] rows) {
        final int[] position = {-1};
        ResultSetMetaData metadata = (ResultSetMetaData) Proxy.newProxyInstance(getClass().getClassLoader(), new Class[]{ResultSetMetaData.class},
            (proxy, method, args) -> {
                switch (method.getName()) {
                    case "getColumnCount": return columns.length;
                    case "getColumnLabel": return columns[(Integer) args[0] - 1];
                    default: throw new SQLFeatureNotSupportedException(method.getName());
                }
            });
        return (ResultSet) Proxy.newProxyInstance(getClass().getClassLoader(), new Class[]{ResultSet.class},
            (proxy, method, args) -> {
                switch (method.getName()) {
                    case "getMetaData": return metadata;
                    case "next": return ++position[0] < rows.length;
                    case "getObject": return rows[position[0]][(Integer) args[0] - 1];
                    case "close": return null;
                    default: throw new SQLFeatureNotSupportedException(method.getName());
                }
            });
    }

    public boolean acceptsURL(String url) { return url.startsWith("jdbc:denodo://"); }
    public DriverPropertyInfo[] getPropertyInfo(String url, Properties info) { return new DriverPropertyInfo[0]; }
    public int getMajorVersion() { return 0; }
    public int getMinorVersion() { return 0; }
    public boolean jdbcCompliant() { return false; }
    public Logger getParentLogger() { return Logger.getGlobal(); }
}
