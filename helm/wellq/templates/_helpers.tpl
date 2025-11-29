{{/*
Expand the name of the chart.
*/}}
{{- define "wellq.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "wellq.fullname" -}}
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
{{- define "wellq.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "wellq.labels" -}}
helm.sh/chart: {{ include "wellq.chart" . }}
{{ include "wellq.selectorLabels" . }}
app.kubernetes.io/version: {{ .Values.app.version | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "wellq.selectorLabels" -}}
app.kubernetes.io/name: {{ include "wellq.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "wellq.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "wellq.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Database connection string
*/}}
{{- define "wellq.databaseUrl" -}}
{{- if .Values.database.external.enabled }}
{{- printf "postgresql://%s:%s@%s:%d/%s" .Values.database.external.user .Values.database.external.password .Values.database.external.host (.Values.database.external.port | int) .Values.database.external.name }}
{{- else }}
{{- $postgresql := .Values.postgresql }}
{{- printf "postgresql://%s:%s@%s-postgresql:%d/%s" $postgresql.auth.username $postgresql.auth.password (include "wellq.fullname" .) 5432 $postgresql.auth.database }}
{{- end }}
{{- end }}

{{/*
Redis connection URL
*/}}
{{- define "wellq.redisUrl" -}}
{{- if .Values.redisExternal.enabled }}
{{- if .Values.redisExternal.password }}
{{- printf "redis://:%s@%s:%d/%d" .Values.redisExternal.password .Values.redisExternal.host (.Values.redisExternal.port | int) (.Values.redisExternal.database | int) }}
{{- else }}
{{- printf "redis://%s:%d/%d" .Values.redisExternal.host (.Values.redisExternal.port | int) (.Values.redisExternal.database | int) }}
{{- end }}
{{- else }}
{{- $redis := .Values.redis }}
{{- if $redis.auth.enabled }}
{{- printf "redis://:%s@%s-redis-master:6379/0" $redis.auth.password (include "wellq.fullname" .) }}
{{- else }}
{{- printf "redis://%s-redis-master:6379/0" (include "wellq.fullname" .) }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Image
*/}}
{{- define "wellq.image" -}}
{{- if .Values.global.imageRegistry }}
{{- printf "%s/%s:%s" .Values.global.imageRegistry .Values.image.repository (.Values.image.tag | default .Chart.AppVersion) }}
{{- else }}
{{- printf "%s/%s:%s" .Values.image.registry .Values.image.repository (.Values.image.tag | default .Chart.AppVersion) }}
{{- end }}
{{- end }}

