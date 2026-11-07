// Mirrors Stylus's variable simplification and Less options. Browser import is a separate gate.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import less from 'less';
import postcss from 'postcss';
import usercssMeta from 'usercss-meta';
import net from 'node:net';
import dgram from 'node:dgram';

// Compilation must fail rather than resolving any new runtime dependency.
net.Socket.prototype.connect = () => { throw new Error('Offline compiler: network denied'); };
dgram.createSocket = () => { throw new Error('Offline compiler: network denied'); };
globalThis.fetch = () => { throw new Error('Offline compiler: network denied'); };

const [exportPath, libraryPath] = process.argv.slice(2);
if (!exportPath || !libraryPath) {
  console.error('Usage: node tests/stylus/check.mjs /path/import.json /path/lib.less');
  process.exit(1);
}

function variables(metadata, saved, flavor) {
  return Object.fromEntries(Object.entries(metadata.vars || {}).map(([key, variable]) => {
    let value = saved[key]?.value ?? variable.default;
    if (key === 'lightFlavor' || key === 'darkFlavor') value = flavor;
    if (['select', 'dropdown', 'image'].includes(variable.type)) {
      const option = variable.options.find(option => option.name === value);
      assert.ok(option, `Invalid ${key}: ${value}`);
      value = option.value;
    } else if (variable.type === 'number' || variable.type === 'range') {
      value = `${value}${variable.units || ''}`;
    }
    return [`@${key}`, value];
  }));
}

const library = await readFile(libraryPath, 'utf8');
const fixture = `${library}
@accentColor: rosewater;
.fixture {
  #lib.palette();
  #lib.defaults();
  #lib.css-variables();
  color: @text;
  background: fade(@accent, 30%);
  border-color: darken(@accent, 5%);
  --rgb: #lib.rgbify(@base)[];
  --hsl: #lib.hslify(@base)[];
  filter: @accent-filter;
  & when (@flavor = latte) { --light-branch: yes; }
  @svg: escape('<svg fill="@{accent}"/>');
  background-image: url('data:image/svg+xml,@{svg}');
}`;
for (const flavor of ['latte', 'mocha']) {
  const {css} = await less.render(fixture, {math: 'parens-division', modifyVars: {'@flavor': flavor}});
  postcss.parse(css);
  assert.match(css, new RegExp(`color-scheme: ${flavor === 'latte' ? 'light' : 'dark'}`));
  assert.equal(css.includes('--light-branch: yes'), flavor === 'latte');
  assert.ok(css.includes('data:image/svg+xml,'));
  assert.ok(!css.includes('@accent-filter'));
}

const records = JSON.parse(await readFile(exportPath, 'utf8'));
let styles = 0;
let sections = 0;
for (const record of records) {
  if (!record.sourceCode) continue;
  const source = record.sourceCode;
  try {
    assert.ok(!/@import\b/.test(source), 'Unbundled import');
    assert.ok(!record.updateUrl && !record.usercssData.updateURL, 'Upstream update URL');
    const {metadata} = usercssMeta.parse(source);
    assert.ok(!metadata.updateURL, 'Update URL in source metadata');
    assert.equal(metadata.preprocessor, 'less');
    assert.equal(metadata.namespace, record.usercssData.namespace);
    for (const flavor of ['latte', 'mocha']) {
      const {css} = await less.render(source, {
        math: 'parens-division',
        javascriptEnabled: false,
        modifyVars: variables(metadata, record.usercssData.vars || {}, flavor),
      });
      const ast = postcss.parse(css);
      let docs = 0;
      ast.walkAtRules('-moz-document', rule => {
        assert.ok(rule.params.trim(), 'Empty document scope');
        assert.ok(rule.nodes.length, 'Empty document section');
        docs++;
      });
      assert.ok(docs, 'No compiled document sections');
      ast.walkAtRules('import', () => assert.fail('Compiled output still imports CSS'));
      sections += docs;
    }
    styles++;
  } catch (error) {
    console.error(`${record.name}: ${error.stack || error}`);
    process.exitCode = 1;
  }
}
if (!process.exitCode) {
  assert.equal(styles, 132, 'Unexpected included style count');
  assert.equal(sections, 310, 'Unexpected document-scope count');
  console.log(`Passed: ${styles} UserCSS styles × 2 flavor paths, ${sections} document sections, helper fixtures.`);
  console.log('This checks metadata + Less + CSS document scopes; actual Stylus import/visual testing remains required.');
}
