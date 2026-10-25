// Site-owned historical mappings are injected when rendering the template.
var legacyRedirects = {};

function handler(event) {
    var request = event.request;
    var uri = request.uri;
    // Static asset directories include historical image files without extensions.
    if (/^\/(assets|css|images)\//.test(uri)) {
        return request;
    }
    var target = legacyRedirects[uri];

    if (!target && uri.endsWith('/index.html')) {
        target = uri.slice(0, -10);
    } else if (!target && !uri.endsWith('/') && uri.split('/').pop().indexOf('.') === -1) {
        target = uri + '/';
    }

    if (target) {
        // A Location starting with // (including browser-normalized backslashes)
        // would select a different host instead of a path on this site.
        target = target.replace(/\\/g, '/').replace(/^\/+/, '/');
        var params = [];
        var query = request.querystring;
        for (var key in query) {
            var values = query[key].multiValue || [query[key]];
            for (var i = 0; i < values.length; i++) {
                // CloudFront supplies the original encoded query components.
                params.push(key + '=' + values[i].value);
            }
        }
        return {
            statusCode: 301,
            statusDescription: 'Moved Permanently',
            headers: { location: { value: target + (params.length ? '?' + params.join('&') : '') } }
        };
    }

    if (uri.endsWith('/')) {
        request.uri += 'index.html';
    }
    return request;
}
