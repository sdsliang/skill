/**
 * 读取「可视化产物 envelope」的标识三件套：id / version / iframe_template。
 * 单一来源是兄弟技能 `chart-component-layout-json-validation` 的 config.js，
 * 本技能不自己维护版本号与入口地址（技能目录同级部署时路径成立）。
 */
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const REL = '../../../../chart-component-layout-json-validation/config.js';

/** @type {{ENVELOPE_ID:string, VERSION:string, IFRAME_TEMPLATE:string}} */
const cfg = require(REL);

export const ENVELOPE = {
    id: cfg.ENVELOPE_ID,
    version: cfg.VERSION,
    iframe_template: cfg.IFRAME_TEMPLATE,
};
