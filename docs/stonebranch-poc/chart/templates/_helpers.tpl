{{- define "stonebranch-uag.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "stonebranch-uag.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- include "stonebranch-uag.name" . -}}
{{- end -}}
{{- end -}}

{{- define "stonebranch-uag.namespace" -}}
{{- .Values.global.namespace -}}
{{- end -}}

{{- define "stonebranch-uag.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "stonebranch-uag.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.global.labels }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{- define "stonebranch-uag.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (printf "%s-agent" (include "stonebranch-uag.fullname" .)) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}
