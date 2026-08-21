{{/*
Expand the name of the chart.
*/}}
{{- define "aks-mcp.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "aks-mcp.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "aks-mcp.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "aks-mcp.labels" -}}
helm.sh/chart: {{ include "aks-mcp.chart" . }}
{{ include "aks-mcp.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "aks-mcp.selectorLabels" -}}
app.kubernetes.io/name: {{ include "aks-mcp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "aks-mcp.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "aks-mcp.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create Azure credentials secret name
*/}}
{{- define "aks-mcp.azureSecretName" -}}
{{- if .Values.azure.existingSecret }}
{{- .Values.azure.existingSecret }}
{{- else }}
{{- printf "%s-azure-credentials" (include "aks-mcp.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Generate OAuth redirect URIs
*/}}
{{- define "aks-mcp.oauthRedirectURIs" -}}
{{- if .Values.oauth.redirectURIs -}}
{{- join "," .Values.oauth.redirectURIs -}}
{{- end -}}
{{- end }}

{{/*
Generate OAuth CORS origins
*/}}
{{- define "aks-mcp.oauthCorsOrigins" -}}
{{- if .Values.oauth.corsOrigins -}}
{{- join "," .Values.oauth.corsOrigins -}}
{{- end -}}
{{- end }}

{{/*
Fail early for invalid or unsafe autoscaling combinations.
*/}}
{{- define "aks-mcp.validateAutoscaling" -}}
{{- $mode := .Values.autoscaling.mode -}}
{{- if not (has $mode (list "disabled" "keda" "hpa")) -}}
{{- fail (printf "autoscaling.mode must be one of disabled, keda, or hpa; got %q" $mode) -}}
{{- end -}}
{{- if and (ne $mode "disabled") (eq .Values.app.transport "stdio") -}}
{{- fail "horizontal autoscaling requires an HTTP transport; app.transport=stdio cannot be exposed by the Service" -}}
{{- end -}}
{{- if and (ne $mode "disabled") (lt (int .Values.autoscaling.minReplicas) 1) -}}
{{- fail "autoscaling.minReplicas must be at least 1 for the always-available MCP endpoint" -}}
{{- end -}}
{{- if lt (int .Values.autoscaling.maxReplicas) (int .Values.autoscaling.minReplicas) -}}
{{- fail "autoscaling.maxReplicas must be greater than or equal to autoscaling.minReplicas" -}}
{{- end -}}
{{- if eq $mode "keda" -}}
{{- $_ := required "autoscaling.keda.prometheus.serverAddress is required when autoscaling.mode=keda" .Values.autoscaling.keda.prometheus.serverAddress -}}
{{- $_ := required "autoscaling.keda.prometheus.query is required when autoscaling.mode=keda" .Values.autoscaling.keda.prometheus.query -}}
{{- if and .Values.autoscaling.keda.authentication.create (empty .Values.autoscaling.keda.authentication.azureWorkloadIdentity.identityId) -}}
{{- fail "autoscaling.keda.authentication.azureWorkloadIdentity.identityId is required when creating the TriggerAuthentication" -}}
{{- end -}}
{{- end -}}
{{- if and .Values.vpa.enabled (ne .Values.vpa.updateMode "Off") -}}
{{- fail "this chart supports VPA in recommendation-only mode; vpa.updateMode must be Off" -}}
{{- end -}}
{{- end }}
