#ifndef RES_STIR_SHAKEN_OOB_H
#define RES_STIR_SHAKEN_OOB_H

#include <curl/curl.h>

#include "asterisk/res_stir_shaken.h"

#define MAX_BASEURL_LENGTH 1024
#define MAX_URL_LENGTH 1536
#define MAX_SS_PROFILENAME_LENGTH 128
#define MAX_DATE_LENGTH 64
#define MAX_PASSPORT_LENGTH 4096 // not strictly enforced
#define MAX_PASSPORTDATED_LENGTH (MAX_PASSPORT_LENGTH + MAX_DATE_LENGTH)
#define MAX_SESSIONNAME_LENGTH 520  // src_tn, dest_tn lengths add up to 520
#define CURL_TIMEOUT 3 // curl timeout

enum pri_stir_shaken_response_code {
    PRI_STIR_SHAKEN_RC_OK = 0,
    PRI_STIR_SHAKEN_RC_DISABLED = 1,
    PRI_STIR_SHAKEN_RC_FAILED = 2,
};

char passport_date_delim = '&'; // delimiter separating identity_hdr_val and date_hdr_val
uint curl_timeout = CURL_TIMEOUT;
char jodi_proxy_base_url[MAX_BASEURL_LENGTH]; // URL for the OOB proxy request
char publish_url[MAX_URL_LENGTH];
uint_fast8_t pri_stir_shaken_enable; // enable S/S on PRI

// S/S profile to be used for PRI attest and verify functions.
// If verification fails, call will never be rejected.
char pri_stir_shaken_profile_name[MAX_SS_PROFILENAME_LENGTH]; 

// memory for curl write callback
struct curl_witeback_memory {
    char *memory;
    size_t size;
};

// Jodi PASSPorT upload and retrieve function
static int jodi_publish_passport(const char *src, const char *dst, const char *identity_hdr_val, const char *date_hdr_val, const char* tag);
static void jodi_fetch_passport(const char *src, const char *dst, char **identity_hdr_val, char **date_hdr_val, const char* tag);

// JIWF-PRI functions
static int pri_stir_shaken_attest_and_publish(const char* src_tn, const char* dest_tn, struct ast_channel *chan, const char* tag);
static int pri_stir_shaken_fetch_and_verify(const char* src_tn, const char* dest_tn, struct ast_channel *chan, const char* tag);
int pri_stir_shaken_outgoing_request(const char* src_tn, const char* rdest, struct ast_channel *chan);
int pri_stir_shaken_incoming_request(const char* src_tn, const char* dest_tn, struct ast_channel *chan);

// read config file and set values
static int read_ss_oob_conf_file(const char *filename);
int res_stir_shaken_oob_init(void);

// curl related functions
static CURL *jodi_curl_setup(struct curl_witeback_memory *curl_wb_buf, const char* tag);
static size_t curl_writeback(void *contents, size_t size, size_t nmemb, void *userp, const char* tag); // curl write callback handler


static CURL *jodi_curl_setup(struct curl_witeback_memory *curl_wb_buf, const char* tag) {
    CURL *curl = curl_easy_init();
    if (!curl) {
        ast_log(AST_LOG_ERROR, "%s: Failed to initialize curl.\n", tag);
        return NULL;
    }

    curl_wb_buf->memory = ast_malloc(1); // Will grow as needed
    curl_wb_buf->size = 0;

    curl_easy_setopt(curl, CURLOPT_USERAGENT, AST_CURL_USER_AGENT);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, curl_writeback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, (void *)curl_wb_buf);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, curl_timeout);
    curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1);

    return curl;
}

// Callback function for writing received data
static size_t curl_writeback(void *contents, size_t size, size_t nmemb, void *userp, const char* tag) {
    size_t realsize = size * nmemb;
    struct curl_witeback_memory *mem = (struct curl_witeback_memory *)userp;

    char *ptr = ast_realloc(mem->memory, mem->size + realsize + 1);
    if(ptr == NULL) {
        ast_log(AST_LOG_ERROR, "%s: Not enough memory!\n", tag);
        return 0;
    }

    mem->memory = ptr;
    memcpy(&(mem->memory[mem->size]), contents, realsize);
    mem->size += realsize;
    mem->memory[mem->size] = 0; // Null-terminate

    return realsize;
}

// OOB passport retrieve from Jodi MS
static void jodi_fetch_passport(const char *src, const char *dst, char **identity_hdr_val, char **date_hdr_val, const char* tag) {
    CURL * curl;
    CURLcode res;
    struct curl_witeback_memory curl_wb_buf;
    *date_hdr_val = NULL;
    *identity_hdr_val = NULL;
    char *get_response_token = NULL;
    char fetch_url[MAX_URL_LENGTH];
    
    curl = jodi_curl_setup(&curl_wb_buf, tag);
    if (!curl) return;
    
    snprintf(fetch_url, MAX_URL_LENGTH, "%s/retrieve/%s/%s",jodi_proxy_base_url, src, dst);
    curl_easy_setopt(curl, CURLOPT_URL, fetch_url);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 0);

    res = curl_easy_perform(curl);
    curl_easy_cleanup(curl);

    if (res != CURLE_OK) {
        ast_log(AST_LOG_ERROR, "%s: curl_easy_perform() failed: %s, URL: %s\n", curl_easy_strerror(res), fetch_url, tag);
        return;
    } else {
        // Parse JSON using Jansson
        struct ast_json_error error;
        struct ast_json *root = ast_json_load_string(curl_wb_buf.memory, &error);
        ast_free(curl_wb_buf.memory);

        if (root) {
            struct ast_json *token = ast_json_object_get(root, "token");
            if(token == NULL) {
                ast_log(AST_LOG_ERROR, "%s: GET 'token' not found.\n", tag);
                return;
            }
            else {
                if (ast_json_typeof(token) == AST_JSON_STRING) {
                    get_response_token = ast_strdup(ast_json_string_get(token));
                } else {
                    ast_log(AST_LOG_ERROR, "%s: GET 'token' not a string.\n", tag);
                    return;
                }
                ast_json_unref(root);
            }
        } else {
            ast_log(AST_LOG_ERROR, "%s: Error parsing JSON: %s\n", tag, error.text);
            return;
        }
    }

    // extract identity_hdr_val and date_hdr_val based on the delimiter
    char *delim_pos = strchr(get_response_token, passport_date_delim);
    if (delim_pos) {
        *delim_pos = '\0';  // Replace delimiter with null terminator to split the string
        *date_hdr_val = ast_strdup(get_response_token);
        *identity_hdr_val = ast_strdup(delim_pos + 1);
    } else {
        *date_hdr_val = NULL;
        *identity_hdr_val = NULL;
    }

}

// OOB passport upload to Jodi MS
static int jodi_publish_passport(const char *src, const char *dst, const char *identity_hdr_val, const char *date_hdr_val, const char* tag) {
    CURL * curl;
    CURLcode res;
    struct curl_slist *headers=NULL;
    struct curl_witeback_memory curl_wb_buf;
    struct ast_json *json;
    char *json_str;
    char *message_str = NULL;
    char passport_dated[MAX_PASSPORTDATED_LENGTH];

    curl = jodi_curl_setup(&curl_wb_buf, tag);
    if (!curl) return 1;
    
    // Format POST data
    snprintf(passport_dated, MAX_PASSPORTDATED_LENGTH, "%s%c%s", date_hdr_val, passport_date_delim, identity_hdr_val);
    json = ast_json_object_create();
    ast_json_object_set(json, "src", ast_json_string_create(src));
    ast_json_object_set(json, "dst", ast_json_string_create(dst));
    ast_json_object_set(json, "passport", ast_json_string_create(passport_dated));
    json_str = ast_json_dump_string_format(json, AST_JSON_COMPACT);
    ast_json_unref(json);
    
    curl_easy_setopt(curl, CURLOPT_URL, publish_url);
    headers = curl_slist_append(headers, "Content-Type: application/json");
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json_str);

    res = curl_easy_perform(curl);
    curl_easy_cleanup(curl);
    curl_slist_free_all(headers);

    // Check for errors
    if (res != CURLE_OK) {
        ast_log(AST_LOG_ERROR, "%s: curl_easy_perform() failed: %s\n", tag, curl_easy_strerror(res));
        return 1;
    } else {
        // make sure you get a OK response
        // {"message": "OK"}
        struct ast_json_error error;
        struct ast_json *root = ast_json_load_string(curl_wb_buf.memory, &error);
        ast_free(curl_wb_buf.memory);

        if (root != NULL) {
            struct ast_json *message = ast_json_object_get(root, "message");
            if(message == NULL) {
                ast_log(AST_LOG_ERROR, "%s: POST 'message' not found.\n", tag);
            }
            else {
                if (ast_json_typeof(message) == AST_JSON_STRING) {
                    message_str = ast_strdup(ast_json_string_get(message));
                } else {
                    ast_log(AST_LOG_ERROR, "%s: POST: 'message' not a string.\n", tag);
                    ast_json_unref(root);
                    return 1;
                }
                ast_json_unref(root);
                if(strncmp(message_str, "OK", 2)) {
                    ast_log(AST_LOG_ERROR, "%s: POST: 'message' not OK.\n", tag);
                    return 1;
                }
            }
        } else {
            ast_log(AST_LOG_ERROR, "%s: jodi_publish_passport Error parsing JSON: %s\n", tag, error.text);
            return 1;
        }
        return 0;
    }
}


static int pri_stir_shaken_attest_and_publish(const char* src_tn, const char* dest_tn, struct ast_channel *chan, const char* tag) {
    const char* tmpgetvar;
	char* identity_hdr_val = NULL;
	char date_hdr_val[64];

	ast_channel_lock(chan);
    tmpgetvar = pbx_builtin_getvar_helper(chan, "SS_ID_HDR");
	if (!ast_strlen_zero(tmpgetvar))  { identity_hdr_val = (char *)ast_malloc(strlen(tmpgetvar) + 1); strcpy(identity_hdr_val, tmpgetvar); }
    tmpgetvar = pbx_builtin_getvar_helper(chan, "SS_DATE_HDR");
	if (!ast_strlen_zero(tmpgetvar)) snprintf(date_hdr_val, MAX_DATE_LENGTH, "%s", tmpgetvar);
	ast_channel_unlock(chan);

    
    if (ast_strlen_zero(identity_hdr_val) || ast_strlen_zero(date_hdr_val)) {
        ast_log(AST_LOG_VERBOSE, "%s: PRI S/S OUT Attempting to create new passport\n", tag);
        enum ast_stir_shaken_as_response_code as_rc;
        struct ast_stir_shaken_as_ctx *ctx = NULL;
        
        // get time
        struct tm tm;
        time_t t = time(NULL);
        gmtime_r(&t, &tm);
        strftime(date_hdr_val, MAX_DATE_LENGTH, "%a, %d %b %Y %T GMT", &tm);

        as_rc = ast_stir_shaken_as_ctx_create(src_tn,
            dest_tn, chan,
            pri_stir_shaken_profile_name,
            tag, &ctx);

        if (as_rc == AST_STIR_SHAKEN_AS_DISABLED) {
            ast_log(AST_LOG_VERBOSE, "%s: AS Disabled\n", tag);
            return 0;
        }
        else if (as_rc != AST_STIR_SHAKEN_AS_SUCCESS) {
            ast_log(AST_LOG_ERROR, "%s: Unable to create context\n", tag);
            return 1;
        }

        as_rc = ast_stir_shaken_attest(ctx, &identity_hdr_val);
        if (as_rc != AST_STIR_SHAKEN_AS_SUCCESS) {
            ast_log(AST_LOG_ERROR, "%s: Failed to create attestation\n", tag);
            return 1;
        }
    }
    else {
        ast_log(AST_LOG_VERBOSE, "%s: PRI S/S OUT Retrieved PASSPorT from channel variables\n", tag);
    }

    if(jodi_publish_passport(src_tn, dest_tn, identity_hdr_val, date_hdr_val, tag)) {
        ast_log(AST_LOG_ERROR, "%s: Failed to upload PASSporT\n", tag);
        return 1;
    }

    return 0;
}

static int pri_stir_shaken_fetch_and_verify(const char* src_tn, const char* dest_tn, struct ast_channel *chan, const char* tag) {
    // fetch PASSporT from Jodi MS
    char *identity_hdr_val;
    char date_hdr_val[MAX_DATE_LENGTH];
    char *date_hdr_val_tmp;
    
    jodi_fetch_passport(src_tn, dest_tn, &identity_hdr_val, &date_hdr_val_tmp, tag);
    if(date_hdr_val_tmp) snprintf(date_hdr_val, MAX_DATE_LENGTH, "%s", date_hdr_val_tmp);

    // ast_log(AST_LOG_VERBOSE, "%s: Downloaded Identity header and date header = %s %s\n", tag, identity_hdr_val, date_hdr_val);


    if(identity_hdr_val == NULL || date_hdr_val_tmp == NULL) {
        ast_log(AST_LOG_ERROR, "%s: Failed to fetch PASSporT\n", tag);
        return 1;
    }

    ast_channel_lock(chan);
	if(pbx_builtin_setvar_helper(chan, "__SS_ID_HDR", identity_hdr_val) == -1 || pbx_builtin_setvar_helper(chan, "__SS_DATE_HDR", date_hdr_val) == -1 ) {
		ast_log(AST_LOG_VERBOSE, "%s: PRI S/S IN Dialplan failed to set SS_ID_HDR or SS_DATE_HDR\n", tag);
        return 1;
    }
	ast_channel_unlock(chan);

    // create ast_ss ctx
    enum ast_stir_shaken_vs_response_code vs_rc;
    struct ast_stir_shaken_vs_ctx *ctx = NULL;

    vs_rc = ast_stir_shaken_vs_ctx_create(src_tn,
		chan,
		pri_stir_shaken_profile_name,
		tag, &ctx);

    if (vs_rc == AST_STIR_SHAKEN_VS_DISABLED) {
        ast_log(AST_LOG_VERBOSE, "%s: VS Disabled\n", tag);
        return 0;
    }
    else if (vs_rc != AST_STIR_SHAKEN_VS_SUCCESS) {
        ast_log(AST_LOG_ERROR, "%s: Unable to create context\n", tag);
        return 1;
    }

    // add identity and date header
    vs_rc = ast_stir_shaken_vs_ctx_add_identity_hdr(ctx, identity_hdr_val);
    if (vs_rc != AST_STIR_SHAKEN_VS_SUCCESS) {
        ast_log(AST_LOG_ERROR, "%s: Unable to add Identity header\n", tag);
        return 1;
    }
    
    vs_rc = ast_stir_shaken_vs_ctx_add_date_hdr(ctx, date_hdr_val);
    if (vs_rc != AST_STIR_SHAKEN_VS_SUCCESS) {
        ast_log(AST_LOG_ERROR, "%s: Unable to add Date header\n", tag);
        return 1;
    }

    // verify PASSporT
    vs_rc = ast_stir_shaken_vs_verify(ctx);
    if (vs_rc != AST_STIR_SHAKEN_VS_SUCCESS) {
        ast_log(AST_LOG_ERROR, "%s: Verification failed\n", tag);
        return 1;
    }
    ast_log(AST_LOG_VERBOSE, "%s: PRI S/S IN Verif success", tag);

    // ast_stir_shaken_add_result_to_channel(ctx);

    return 0;
}

int pri_stir_shaken_outgoing_request(const char* src_tn, const char* rdest, struct ast_channel *chan) {
    char session_name[MAX_SESSIONNAME_LENGTH];
	const char *dest_tn;
    if (pri_stir_shaken_enable) {
		const char *slash = strchr(rdest, '/');
		if (slash) dest_tn = slash + 1;  // Move past the slash
		else dest_tn = rdest;  // No slash, assume number starts at beginning

		snprintf(session_name, MAX_SESSIONNAME_LENGTH, "PRI_%s_%s", src_tn, dest_tn);

        if( pri_stir_shaken_attest_and_publish(src_tn, dest_tn, chan, session_name) ) {
			ast_log(AST_LOG_ERROR, "%s: PRI S/S OUT - pri_stir_shaken_attest_and_publish failed", session_name);
            return PRI_STIR_SHAKEN_RC_FAILED;
        }
	}
    else {
        ast_log(AST_LOG_VERBOSE, "%s: JIWF outgoing disabled", session_name);
        return PRI_STIR_SHAKEN_RC_DISABLED;
    }

    ast_log(AST_LOG_VERBOSE, "%s: JIWF outgoing success", session_name);
    return PRI_STIR_SHAKEN_RC_OK;
}

int pri_stir_shaken_incoming_request(const char* src_tn, const char* dest_tn, struct ast_channel *chan) {
    char session_name[MAX_SESSIONNAME_LENGTH];
    if (pri_stir_shaken_enable) {
		snprintf(session_name, MAX_SESSIONNAME_LENGTH, "PRI_%s_%s", src_tn, dest_tn);

		// TODO: skip this step if provider is mediating
		if( pri_stir_shaken_fetch_and_verify(src_tn, dest_tn, chan, session_name) ) {
			ast_log(AST_LOG_ERROR, "%s: PRI S/S IN - pri_stir_shaken_fetch_and_verify failed", session_name);
            return PRI_STIR_SHAKEN_RC_FAILED;
        }
	}
    else {
        ast_log(AST_LOG_VERBOSE, "%s: JIWF incoming disabled", session_name);
        return PRI_STIR_SHAKEN_RC_DISABLED;
    }

    ast_log(AST_LOG_VERBOSE, "%s: JIWF incoming success", session_name);
    return PRI_STIR_SHAKEN_RC_OK;
}

static int read_ss_oob_conf_file(const char *filename) {
    struct ast_json_error error;
    struct ast_json *root = ast_json_load_new_file(filename, &error);

    if(root == NULL) {
        ast_log(AST_LOG_ERROR, "S/S OOB Error reading from file: %s\n", filename);
        return 1;
    }

    // pri_stir_shaken_enable (bool) 
    {
        struct ast_json *enable_val = ast_json_object_get(root, "pri_stir_shaken_enable");
        if (enable_val == NULL) pri_stir_shaken_enable = 0;
        if (ast_json_is_true(enable_val)) pri_stir_shaken_enable = 1;
        else pri_stir_shaken_enable = 0;
    }

    // pri_stir_shaken_profile_name (string) 
    {
        struct ast_json *profile_val = ast_json_object_get(root, "pri_stir_shaken_profile_name");
        if (ast_json_typeof(profile_val) == AST_JSON_STRING) {
            snprintf(pri_stir_shaken_profile_name, MAX_SS_PROFILENAME_LENGTH, "%s",ast_json_string_get(profile_val));
        } else {
            return 1;
        }
    }

    // oob_proxy_url -> jodi_proxy_base_url (string) 
    {
        struct ast_json *url_val = ast_json_object_get(root, "oob_proxy_url");
        if (ast_json_typeof(url_val) == AST_JSON_STRING) {
            snprintf(jodi_proxy_base_url, MAX_BASEURL_LENGTH, "%s", ast_json_string_get(url_val));
            snprintf(publish_url, MAX_URL_LENGTH, "%s/publish", jodi_proxy_base_url);
        } else {
            return 1;
        }
    }

    // Clean up JSON object 
    ast_json_unref(root);

    return 0;
}

int res_stir_shaken_oob_init() {

    if (read_ss_oob_conf_file("/etc/asterisk/stir_shaken.oob.conf"))
		return 1;
    ast_log(AST_LOG_VERBOSE, "S/S OOB: pri_stir_shaken_enable, jodi_proxy_base_url, pri_stir_shaken_profile_name = %d, %s, %s\n", pri_stir_shaken_enable, jodi_proxy_base_url, pri_stir_shaken_profile_name);

    return 0;
}

#endif