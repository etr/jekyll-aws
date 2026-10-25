const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

function route(uri, querystring = {}, redirects = {}) {
  const file = path.join(__dirname, '../cloudfront/clean-urls.js');
  const code = fs.readFileSync(file, 'utf8');
  const context = vm.createContext({});
  vm.runInContext(code.replace('var legacyRedirects = {};', `var legacyRedirects = ${JSON.stringify(redirects)};`), context);
  return JSON.parse(JSON.stringify(context.handler({ request: {
    method: 'GET', uri, querystring, headers: {}, cookies: {},
  } })));
}

for (const [uri, target] of [['/', '/index.html'], ['/post/', '/post/index.html'], ['/a.b/post/', '/a.b/post/index.html']]) {
  test(`${uri} resolves its directory index`, () => {
    assert.equal(route(uri).uri, target);
  });
}

for (const [uri, target] of [['/post', '/post/'], ['/post/index.html', '/post/'], ['/index.html', '/']]) {
  test(`${uri} redirects to its canonical URL`, () => {
    const response = route(uri);
    assert.equal(response.statusCode, 301);
    assert.equal(response.headers.location.value, target);
  });
}

for (const uri of ['/css/style.css', '/feed.xml', '/404.html', '/tools/example.html', '/image.webp', '/assets/img/posts/example-image', '/images/extensionless-image']) {
  test(`${uri} remains addressable as a real file`, () => {
    assert.equal(route(uri).uri, uri);
  });
}

test('redirects retain encoded, empty, and repeated query parameters', () => {
  const response = route('/post', {
    utm_source: { value: 'test' },
    next: { value: '%2Ftools%3Fx%3D1' },
    empty: { value: '' },
    tag: { value: 'first', multiValue: [{ value: 'first' }, { value: 'a+b' }] },
  });
  assert.equal(response.headers.location.value,
    '/post/?utm_source=test&next=%2Ftools%3Fx%3D1&empty=&tag=first&tag=a+b');
});

test('internal rewrites preserve query strings', () => {
  assert.deepEqual(route('/post/', { x: { value: '1' } }).querystring, { x: { value: '1' } });
});

test('only declared legacy HTML paths redirect', () => {
  const response = route('/archive/example-post.html', { x: { value: '1' } }, {
    '/archive/example-post.html': '/posts/example-post/',
  });
  assert.equal(response.statusCode, 301);
  assert.equal(response.headers.location.value, '/posts/example-post/?x=1');
});

for (const uri of ['//outside.example/page', '//outside.example/index.html', '/\\outside.example/page']) {
  test(`${uri} cannot produce a redirect to another host`, () => {
    const response = route(uri);
    assert.equal(response.statusCode, 301);
    assert.equal(response.headers.location.value,
      uri.endsWith('index.html') ? '/outside.example/' : '/outside.example/page/');
  });
}
