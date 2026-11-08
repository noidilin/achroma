// The optional standalone style is plain CSS, not an extra backup record.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import postcss from 'postcss';
import usercssMeta from 'usercss-meta';

const [stylePath, lightPath, darkPath] = process.argv.slice(2);
assert.ok(stylePath && lightPath && darkPath,
  'Usage: node check-complement.mjs style.user.css light.json dark.json');
const source = await readFile(stylePath, 'utf8');
const {metadata, errors} = usercssMeta.parse(source);
assert.ok(!errors?.length, 'Invalid UserCSS metadata');
assert.equal(metadata.name, 'Achroma complement');
assert.equal(metadata.namespace, 'https://github.com/noidilin/achroma/complement');
assert.equal(metadata.license, 'MIT');
assert.ok(!metadata.updateURL && !metadata.preprocessor);
assert.doesNotMatch(source, /@import\b|url\(|\{\{/i);
const ast = postcss.parse(source);
const documents = [];
const roots = [];
ast.walkAtRules('-moz-document', rule => documents.push(rule));
ast.walkRules(':root', rule => roots.push(rule));
assert.equal(documents.length, 5);
assert.equal(roots.length, 2);
assert.equal(roots[0].parent, documents[0]);
assert.equal(roots[1].parent.name, 'media');
assert.equal(roots[1].parent.params, '(prefers-color-scheme: dark)');
assert.equal(roots[1].parent.parent, documents[0]);
assert.equal(documents[0].params, 'regexp(".*")');
assert.equal(documents[2].params, 'domain("www.youtube.com")');
assert.equal(documents[3].params, 'domain("linux.vbird.org")');
assert.equal(documents[4].params, 'domain("boot.dev")');
const prefix = '--achroma-complement-';
const references = [...source.matchAll(/var\((--achroma-complement-\w+)\)/g)].map(match => match[1]);
const palettes = await Promise.all([lightPath, darkPath].map(async path =>
  JSON.parse(await readFile(path, 'utf8'))));
for (const [index, root] of roots.entries()) {
  const properties = new Map(root.nodes.map(node => [node.prop, node.value]));
  assert.equal(properties.size, root.nodes.length, 'Duplicate palette variable');
  assert.deepEqual([...properties.keys()].sort(), [...new Set(references)].sort());
  for (const [property, color] of properties) {
    assert.equal(color, palettes[index][property.slice(prefix.length)]);
  }
}
ast.walkDecls(declaration => {
  if (declaration.prop.startsWith(prefix)) return;
  assert.doesNotMatch(declaration.value, /#[0-9a-f]{3,8}\b|rgba?\(/i, 'Hardcoded color outside palettes');
});
// Evaluate the retained exclusion expression after CSS-string unescaping.
const condition = documents[1].params.match(/^regexp\((".*")\)$/);
assert.ok(condition);
const expression = new RegExp(JSON.parse(condition[1]));
for (const url of ['https://monkeytype.com/', 'https://monkeytype.com/test',
  'http://localhost:3000/', 'http://localhost:5173/path', 'https://tweakcn.com/']) {
  assert.equal(expression.test(url), false, `Rendering must remain excluded on ${url}`);
}
for (const url of ['https://example.com/', 'https://www.youtube.com/watch?v=test',
  'http://localhost:3001/']) {
  assert.equal(expression.test(url), true);
}
assert.ok(documents[0].nodes.some(node => node.selector === '.leechblock-timer'));
assert.ok(documents[1].nodes.some(node => node.selector === 'body'));
assert.ok(documents[3].nodes.some(node => node.selector?.includes('img[alt*="鳥哥"]')));
console.log('Passed: optional complement metadata, 5 scopes, light/dark palettes and rendering exclusions.');
console.log('Manual Stylus import and visual review remain required; nothing was installed.');
