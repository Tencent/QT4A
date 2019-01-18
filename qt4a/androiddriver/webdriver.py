# -*- coding: utf-8 -*-
#
# Tencent is pleased to support the open source community by making QTA available.
# Copyright (C) 2016THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the BSD 3-Clause License (the "License"); you may not use this 
# file except in compliance with the License. You may obtain a copy of the License at
# 
# https://opensource.org/licenses/BSD-3-Clause
# 
# Unless required by applicable law or agreed to in writing, software distributed 
# under the License is distributed on an "AS IS" basis, WITHOUT WARRANTIES OR CONDITIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.
#

'''Web页面测试桩代理
'''

import time

# XPath库 Android 2.3以下不支持XPath
# http://www.llamalab.com/js/xpath/XPath.js #该库不支持前后括号情况
# http://coderepos.org/share/wiki/JavaScript-XPath

xpath_lib_str = '''
/*  JavaScript-XPath 0.1.12
 *  (c) 2007 Cybozu Labs, Inc.
 *
 *  JavaScript-XPath is freely distributable under the terms of an MIT-style license.
 *  For details, see the JavaScript-XPath web site: http://coderepos.org/share/wiki/JavaScript-XPath
 *
 */
window.jsxpath={"exportInstaller": true};
(function() {
    var ca = void(0);
    var da = {
        targetFrame: ca,
        exportInstaller: false,
        useNative: true,
        useInnerText: true
    };
    var ea;
    if (window.jsxpath) {
        ea = window.jsxpath;
    } else {
        var fa = document.getElementsByTagName('script');
        var ga = fa[fa.length - 1];
        var ha = ga.src;
        ea = {};
        var ia = ha.match(/\?(.*)$/);
        if (ia) {
            var ja = ia[1].split('&');
            for (var i = 0,
            l = ja.length; i < l; i++) {
                var ka = ja[i];
                var la = ka.split('=');
                var ma = la[0];
                var na = la[1];
                if (na == ca) {
                    na == true;
                } else if (na == 'false' || /^-?\d+$/.test(na)) {
                    na = eval(na);
                }
                ea[ma] = na;
            }
        }
    }
    for (var n in da) {
        if (! (n in ea)) ea[n] = da[n];
    }
    ea.hasNative = !!(document.implementation && document.implementation.hasFeature && document.implementation.hasFeature("XPath", null));
    if (ea.hasNative && ea.useNative && !ea.exportInstaller) {
        return;
    }
    var oa;
    var pa;
    var qa;
    var ra;
    var sa;
    var ta;
    var va;
    var wa;
    var xa;
    var ya;
    var za;
    var Aa;
    var Ba;
    var Ca;
    var Da = new
    function() {
        var ua = navigator.userAgent;
        if (RegExp == ca) {
            if (ua.indexOf("Opera") >= 0) {
                this.opera = true;
            } else if (ua.indexOf("Netscape") >= 0) {
                this.netscape = true;
            } else if (ua.indexOf("Mozilla/") == 0) {
                this.mozilla = true;
            } else {
                this.unknown = true;
            }
            if (ua.indexOf("Gecko/") >= 0) {
                this.gecko = true;
            }
            if (ua.indexOf("Win") >= 0) {
                this.windows = true;
            } else if (ua.indexOf("Mac") >= 0) {
                this.mac = true;
            } else if (ua.indexOf("Linux") >= 0) {
                this.linux = true;
            } else if (ua.indexOf("BSD") >= 0) {
                this.bsd = true;
            } else if (ua.indexOf("SunOS") >= 0) {
                this.sunos = true;
            }
        } else {
            if (/AppleWebKit\/(\d+(?:\.\d+)*)/.test(ua)) {
                this.applewebkit = RegExp.$1;
                if (RegExp.$1.charAt(0) == 4) {
                    this.applewebkit2 = true;
                } else {
                    this.applewebkit3 = true;
                }
            } else if (typeof Components == "object" && (/Gecko\/(\d{8})/.test(ua) || navigator.product == "Gecko" && /^(\d{8})$/.test(navigator.productSub))) {
                this.gecko = RegExp.$1;
            }

            if (typeof(opera) == "object" && typeof(opera.version) == "function") {
                this.opera = opera.version();
                this['opera' + this.opera[0] + this.opera[2]] = true;
            } else if (typeof opera == "object" && (/Opera[\/ ](\d+\.\d+)/.test(ua))) {
                this.opera = RegExp.$1;
            } else if (this.ie) {} else if (/Safari\/(\d+(?:\.\d+)*)/.test(ua)) {
                this.safari = RegExp.$1;
            } else if (/NetFront\/(\d+(?:\.\d+)*)/.test(ua)) {
                this.netfront = RegExp.$1;
            } else if (/Konqueror\/(\d+(?:\.\d+)*)/.test(ua)) {
                this.konqueror = RegExp.$1;
            } else if (ua.indexOf("(compatible;") < 0 && (/^Mozilla\/(\d+\.\d+)/.test(ua))) {
                this.mozilla = RegExp.$1;
                if (/\([^(]*rv:(\d+(?:\.\d+)*).*?\)/.test(ua)) this.mozillarv = RegExp.$1;
                if (/Firefox\/(\d+(?:\.\d+)*)/.test(ua)) {
                    this.firefox = RegExp.$1;
                } else if (/Netscape\d?\/(\d+(?:\.\d+)*)/.test(ua)) {
                    this.netscape = RegExp.$1;
                }
            } else {
                this.unknown = true;
            }
            if (ua.indexOf("Win 9x 4.90") >= 0) {
                this.windows = "ME";
            } else if (/Win(?:dows)? ?(NT ?(\d+\.\d+)?|\d+|ME|Vista|XP)/.test(ua)) {
                this.windows = RegExp.$1;
                if (RegExp.$2) {
                    this.winnt = RegExp.$2;
                } else switch (RegExp.$1) {
                case "2000":
                    this.winnt = "5.0";
                    break;
                case "XP":
                    this.winnt = "5.1";
                    break;
                case "Vista":
                    this.winnt = "6.0";
                    break;
                }
            } else if (ua.indexOf("Mac") >= 0) {
                this.mac = true;
            } else if (ua.indexOf("Linux") >= 0) {
                this.linux = true;
            } else if (/(\w*BSD)/.test(ua)) {
                this.bsd = RegExp.$1;
            } else if (ua.indexOf("SunOS") >= 0) {
                this.sunos = true;
            }
        }
    };
    var Ea = function(Fa) {
        var Ga = Ea.prototype;
        var Ha = Fa.match(Ga.regs.token);
        for (var i = 0,
        l = Ha.length; i < l; i++) {
            if (Ga.regs.strip.test(Ha[i])) {
                Ha.splice(i, 1);
            }
        }
        for (var n in Ga) Ha[n] = Ga[n];
        Ha.index = 0;
        return Ha;
    };
    Ea.prototype.regs = {
        token: /\$?(?:(?![0-9-])[\w-]+:)?(?![0-9-])[\w-]+|\/\/|\.\.|::|\d+(?:\.\d*)?|\.\d+|"[^"]*"|'[^']*'|[!<>]=|(?![0-9-])[\w-]+:\*|\s+|./g,
        strip: /^\s/
    };
    Ea.prototype.peek = function(i) {
        return this[this.index + (i || 0)];
    };
    Ea.prototype.next = function() {
        return this[this.index++];
    };
    Ea.prototype.back = function() {
        this.index--;
    };
    Ea.prototype.empty = function() {
        return this.length <= this.index;
    };
    var Ia = function(Ja, Ka, La) {
        this.node = Ja;
        this.position = Ka || 1;
        this.last = La || 1;
    };
    var Ma = function() {};
    Ma.prototype.number = function(Na) {
        var Oa = this.evaluate(Na);
        if (Oa.isNodeSet) return Oa.number();
        return + Oa;
    };
    Ma.prototype.string = function(Pa) {
        var Qa = this.evaluate(Pa);
        if (Qa.isNodeSet) return Qa.string();
        return '' + Qa;
    };
    Ma.prototype.bool = function(Ra) {
        var Sa = this.evaluate(Ra);
        if (Sa.isNodeSet) return Sa.bool();
        return !! Sa;
    };
    var Ta = function() {};
    Ta.parsePredicates = function(Ua, Va) {
        while (Ua.peek() == '[') {
            Ua.next();
            if (Ua.empty()) {
                throw Error('missing predicate expr');
            }
            var Wa = oa.parse(Ua);
            Va.predicate(Wa);
            if (Ua.empty()) {
                throw Error('unclosed predicate expr');
            }
            if (Ua.next() != ']') {
                Ua.back();
                throw Error('bad token: ' + Ua.next());
            }
        }
    };
    Ta.prototype = new Ma();
    Ta.prototype.evaluatePredicates = function(Xa, Ya) {
        var Za, predicate, nodes, node, Xa, position, reverse;
        reverse = this.reverse;
        Za = this.predicates;
        Xa.sort();
        for (var i = Ya || 0,
        l0 = Za.length; i < l0; i++) {
            predicate = Za[i];
            var $a = [];
            var ab = Xa.list();
            for (var j = 0,
            l1 = ab.length; j < l1; j++) {
                position = reverse ? (l1 - j) : (j + 1);
                exrs = predicate.evaluate(new Ia(ab[j], position, l1));
                switch (typeof exrs) {
                case 'number':
                    exrs = (position == exrs);
                    break;
                case 'string':
                    exrs = !!exrs;
                    break;
                case 'object':
                    exrs = exrs.bool();
                    break;
                }
                if (!exrs) {
                    $a.push(j);
                }
            }
            for (var j = $a.length - 1,
            l1 = 0; j >= l1; j--) {
                Xa.del($a[j]);
            }
        }
        return Xa;
    };
    if (!window.BinaryExpr && window.defaultConfig) window.BinaryExpr = null;
    oa = function(op, bb, cb, db) {
        this.op = op;
        this.left = bb;
        this.right = cb;
        this.datatype = oa.ops[op][2];
        this.needContextPosition = bb.needContextPosition || cb.needContextPosition;
        this.needContextNode = bb.needContextNode || cb.needContextNode;
        if (this.op == '=') {
            if (!cb.needContextNode && !cb.needContextPosition && cb.datatype != 'nodeset' && cb.datatype != 'void' && bb.quickAttr) {
                this.quickAttr = true;
                this.attrName = bb.attrName;
                this.attrValueExpr = cb;
            } else if (!bb.needContextNode && !bb.needContextPosition && bb.datatype != 'nodeset' && bb.datatype != 'void' && cb.quickAttr) {
                this.quickAttr = true;
                this.attrName = cb.attrName;
                this.attrValueExpr = bb;
            }
        }
    };
    oa.compare = function(op, eb, fb, gb, hb) {
        var ib, lnodes, rnodes, nodes, nodeset, primitive;
        fb = fb.evaluate(hb);
        gb = gb.evaluate(hb);
        if (fb.isNodeSet && gb.isNodeSet) {
            lnodes = fb.list();
            rnodes = gb.list();
            for (var i = 0,
            l0 = lnodes.length; i < l0; i++) for (var j = 0,
            l1 = rnodes.length; j < l1; j++) if (eb(wa.to('string', lnodes[i]), wa.to('string', rnodes[j]))) return true;
            return false;
        }
        if (fb.isNodeSet || gb.isNodeSet) {
            if (fb.isNodeSet) nodeset = fb,
            primitive = gb;
            else nodeset = gb,
            primitive = fb;
            nodes = nodeset.list();
            ib = typeof primitive;
            for (var i = 0,
            l = nodes.length; i < l; i++) {
                if (eb(wa.to(ib, nodes[i]), primitive)) return true;
            }
            return false;
        }
        if (op == '=' || op == '!=') {
            if (typeof fb == 'boolean' || typeof gb == 'boolean') {
                return eb( !! fb, !!gb);
            }
            if (typeof fb == 'number' || typeof gb == 'number') {
                return eb( + fb, +gb);
            }
            return eb(fb, gb);
        }
        return eb( + fb, +gb);
    };
    oa.ops = {
        'div': [6,
        function(jb, kb, lb) {
            return jb.number(lb) / kb.number(lb);
        },
        'number'],
        'mod': [6,
        function(mb, nb, ob) {
            return mb.number(ob) % nb.number(ob);
        },
        'number'],
        '*': [6,
        function(pb, qb, rb) {
            return pb.number(rb) * qb.number(rb);
        },
        'number'],
        '+': [5,
        function(sb, tb, ub) {
            return sb.number(ub) + tb.number(ub);
        },
        'number'],
        '-': [5,
        function(vb, wb, xb) {
            return vb.number(xb) - wb.number(xb);
        },
        'number'],
        '<': [4,
        function(yb, zb, Ab) {
            return oa.compare('<',
            function(a, b) {
                return a < b
            },
            yb, zb, Ab);
        },
        'boolean'],
        '>': [4,
        function(Bb, Cb, Db) {
            return oa.compare('>',
            function(a, b) {
                return a > b
            },
            Bb, Cb, Db);
        },
        'boolean'],
        '<=': [4,
        function(Eb, Fb, Gb) {
            return oa.compare('<=',
            function(a, b) {
                return a <= b
            },
            Eb, Fb, Gb);
        },
        'boolean'],
        '>=': [4,
        function(Hb, Ib, Jb) {
            return oa.compare('>=',
            function(a, b) {
                return a >= b
            },
            Hb, Ib, Jb);
        },
        'boolean'],
        '=': [3,
        function(Kb, Lb, Mb) {
            return oa.compare('=',
            function(a, b) {
                return a == b
            },
            Kb, Lb, Mb);
        },
        'boolean'],
        '!=': [3,
        function(Nb, Ob, Pb) {
            return oa.compare('!=',
            function(a, b) {
                return a != b
            },
            Nb, Ob, Pb);
        },
        'boolean'],
        'and': [2,
        function(Qb, Rb, Sb) {
            return Qb.bool(Sb) && Rb.bool(Sb);
        },
        'boolean'],
        'or': [1,
        function(Tb, Ub, Vb) {
            return Tb.bool(Vb) || Ub.bool(Vb);
        },
        'boolean']
    };
    oa.parse = function(Wb) {
        var op, precedence, info, expr, stack = [],
        index = Wb.index;
        while (true) {
            if (Wb.empty()) {
                throw Error('missing right expression');
            }
            expr = Aa.parse(Wb);
            op = Wb.next();
            if (!op) {
                break;
            }
            info = this.ops[op];
            precedence = info && info[0];
            if (!precedence) {
                Wb.back();
                break;
            }
            while (stack.length && precedence <= this.ops[stack[stack.length - 1]][0]) {
                expr = new oa(stack.pop(), stack.pop(), expr);
            }
            stack.push(expr, op);
        }
        while (stack.length) {
            expr = new oa(stack.pop(), stack.pop(), expr);
        }
        return expr;
    };
    oa.prototype = new Ma();
    oa.prototype.evaluate = function(Xb) {
        return oa.ops[this.op][1](this.left, this.right, Xb);
    };
    oa.prototype.show = function(Yb) {
        Yb = Yb || '';
        var t = '';
        t += Yb + 'binary: ' + this.op + '\\n';
        Yb += '    ';
        t += this.left.show(Yb);
        t += this.right.show(Yb);
        return t;
    };
    if (!window.UnaryExpr && window.defaultConfig) window.UnaryExpr = null;
    Aa = function(op, Zb) {
        this.op = op;
        this.expr = Zb;
        this.needContextPosition = Zb.needContextPosition;
        this.needContextNode = Zb.needContextNode;
    };
    Aa.ops = {
        '-': 1
    };
    Aa.parse = function($b) {
        var ac;
        if (this.ops[$b.peek()]) return new Aa($b.next(), Aa.parse($b));
        else return Ba.parse($b);
    };
    Aa.prototype = new Ma();
    Aa.prototype.datatype = 'number';
    Aa.prototype.evaluate = function(bc) {
        return - this.expr.number(bc);
    };
    Aa.prototype.show = function(cc) {
        cc = cc || '';
        var t = '';
        t += cc + 'unary: ' + this.op + '\\n';
        cc += '    ';
        t += this.expr.show(cc);
        return t;
    };
    if (!window.UnionExpr && window.defaultConfig) window.UnionExpr = null;
    Ba = function() {
        this.paths = [];
    };
    Ba.ops = {
        '|': 1
    };
    Ba.parse = function(dc) {
        var ec, expr;
        expr = ya.parse(dc);
        if (!this.ops[dc.peek()]) return expr;
        ec = new Ba();
        ec.path(expr);
        while (true) {
            if (!this.ops[dc.next()]) break;
            if (dc.empty()) {
                throw Error('missing next union location path');
            }
            ec.path(ya.parse(dc));
        }
        dc.back();
        return ec;
    };
    Ba.prototype = new Ma();
    Ba.prototype.datatype = 'nodeset';
    Ba.prototype.evaluate = function(fc) {
        var gc = this.paths;
        var hc = new ta();
        for (var i = 0,
        l = gc.length; i < l; i++) {
            var ic = gc[i].evaluate(fc);
            if (!ic.isNodeSet) throw Error('PathExpr must be nodeset');
            hc.merge(ic);
        }
        return hc;
    };
    Ba.prototype.path = function(jc) {
        this.paths.push(jc);
        if (jc.needContextPosition) {
            this.needContextPosition = true;
        }
        if (jc.needContextNode) {
            this.needContextNode = true;
        }
    }
    Ba.prototype.show = function(kc) {
        kc = kc || '';
        var t = '';
        t += kc + 'union:' + '\\n';
        kc += '    ';
        for (var i = 0; i < this.paths.length; i++) {
            t += this.paths[i].show(kc);
        }
        return t;
    };
    if (!window.PathExpr && window.defaultConfig) window.PathExpr = null;
    ya = function(lc) {
        this.filter = lc;
        this.steps = [];
        this.datatype = lc.datatype;
        this.needContextPosition = lc.needContextPosition;
        this.needContextNode = lc.needContextNode;
    };
    ya.ops = {
        '//': 1,
        '/': 1
    };
    ya.parse = function(mc) {
        var op, expr, path, token;
        if (this.ops[mc.peek()]) {
            op = mc.next();
            token = mc.peek();
            if (op == '/' && (mc.empty() || (token != '.' && token != '..' && token != '@' && token != '*' && !/(?![0-9])[\w]/.test(token)))) {
                return pa.root();
            }
            path = new ya(pa.root());
            if (mc.empty()) {
                throw Error('missing next location step');
            }
            expr = za.parse(mc);
            path.step(op, expr);
        } else {
            expr = pa.parse(mc);
            if (!expr) {
                expr = za.parse(mc);
                path = new ya(pa.context());
                path.step('/', expr);
            } else if (!this.ops[mc.peek()]) return expr;
            else path = new ya(expr);
        }
        while (true) {
            if (!this.ops[mc.peek()]) break;
            op = mc.next();
            if (mc.empty()) {
                throw Error('missing next location step');
            }
            path.step(op, za.parse(mc));
        }
        return path;
    };
    ya.prototype = new Ma();
    ya.prototype.evaluate = function(nc) {
        var oc = this.filter.evaluate(nc);
        if (!oc.isNodeSet) throw Exception('Filter nodeset must be nodeset type');
        var pc = this.steps;
        for (var i = 0,
        l0 = pc.length; i < l0 && oc.length; i++) {
            var qc = pc[i][1];
            var rc = qc.reverse;
            var sc = oc.iterator(rc);
            var tc = oc;
            oc = null;
            var uc, next;
            if (!qc.needContextPosition && qc.axis == 'following') {
                for (uc = sc(); next = sc(); uc = next) {
                    if (Da.applewebkit2) {
                        var vc = false;
                        var wc = next;
                        do {
                            if (wc == uc) {
                                vc = true;
                                break;
                            }
                        } while ( wc = wc . parentNode );
                        if (!vc) break;
                    } else {
                        try {
                            if (!uc.contains(next)) break
                        } catch(e) {
                            if (! (next.compareDocumentPosition(uc) & 8)) break
                        }
                    }
                }
                oc = qc.evaluate(new Ia(uc));
            } else if (!qc.needContextPosition && qc.axis == 'preceding') {
                uc = sc();
                oc = qc.evaluate(new Ia(uc));
            } else {
                uc = sc();
                var j = 0;
                oc = qc.evaluate(new Ia(uc), false, tc, j);
                while (uc = sc()) {
                    j++;
                    oc.merge(qc.evaluate(new Ia(uc), false, tc, j));
                }
            }
        }
        return oc;
    };
    ya.prototype.step = function(op, xc) {
        xc.op = op;
        this.steps.push([op, xc]);
        this.quickAttr = false;
        if (this.steps.length == 1) {
            if (op == '/' && xc.axis == 'attribute') {
                var yc = xc.test;
                if (!yc.notOnlyElement && yc.name != '*') {
                    this.quickAttr = true;
                    this.attrName = yc.name;
                }
            }
        }
    };
    ya.prototype.show = function(zc) {
        zc = zc || '';
        var t = '';
        t += zc + 'path:' + '\\n';
        zc += '    ';
        t += zc + 'filter:' + '\\n';
        t += this.filter.show(zc + '    ');
        if (this.steps.length) {
            t += zc + 'steps:' + '\\n';
            zc += '    ';
            for (var i = 0; i < this.steps.length; i++) {
                var Ac = this.steps[i];
                t += zc + 'operator: ' + Ac[0] + '\\n';
                t += Ac[1].show(zc);
            }
        }
        return t;
    };
    if (!window.FilterExpr && window.defaultConfig) window.FilterExpr = null;
    pa = function(Bc) {
        this.primary = Bc;
        this.predicates = [];
        this.datatype = Bc.datatype;
        this.needContextPosition = Bc.needContextPosition;
        this.needContextNode = Bc.needContextNode;
    };
    pa.parse = function(Cc) {
        var Dc, filter, token, ch;
        token = Cc.peek();
        ch = token.charAt(0);
        switch (ch) {
        case '$':
            Dc = Ca.parse(Cc);
            break;
        case '(':
            Cc.next();
            Dc = oa.parse(Cc);
            if (Cc.empty()) {
                throw Error('unclosed "("');
            }
            if (Cc.next() != ')') {
                Cc.back();
                throw Error('bad token: ' + Cc.next());
            }
            break;
        case '"':
        case "'":
            Dc = ra.parse(Cc);
            break;
        default:
            if (!isNaN( + token)) {
                Dc = xa.parse(Cc);
            } else if (va.types[token]) {
                return null;
            } else if (/(?![0-9])[\w]/.test(ch) && Cc.peek(1) == '(') {
                Dc = qa.parse(Cc);
            } else {
                return null;
            }
            break;
        }
        if (Cc.peek() != '[') return Dc;
        filter = new pa(Dc);
        Ta.parsePredicates(Cc, filter);
        return filter;
    };
    pa.root = function() {
        return new qa('root-node');
    };
    pa.context = function() {
        return new qa('context-node');
    };
    pa.prototype = new Ta();
    pa.prototype.evaluate = function(Ec) {
        var Fc = this.primary.evaluate(Ec);
        if (!Fc.isNodeSet) {
            if (this.predicates.length) throw Error('Primary result must be nodeset type ' + 'if filter have predicate expression');
            return Fc;
        }
        return this.evaluatePredicates(Fc);
    };
    pa.prototype.predicate = function(Gc) {
        this.predicates.push(Gc);
    };
    pa.prototype.show = function(Hc) {
        Hc = Hc || '';
        var t = '';
        t += Hc + 'filter: ' + '\\n';
        Hc += '    ';
        t += this.primary.show(Hc);
        if (this.predicates.length) {
            t += Hc + 'predicates: ' + '\\n';
            Hc += '    ';
            for (var i = 0; i < this.predicates.length; i++) {
                t += this.predicates[i].show(Hc);
            }
        }
        return t;
    };
    if (!window.NodeUtil && window.defaultConfig) window.NodeUtil = null;
    wa = {
        to: function(Ic, Jc) {
            var t, type = Jc.nodeType;
            if (type == 1 && ea.useInnerText && !Da.applewebkit2) {
                t = Jc.textContent;
                t = (t == ca || t == null) ? Jc.innerText: t;
                t = (t == ca || t == null) ? '': t;
            }
            if (typeof t != 'string') {
                if (type == 9 || type == 1) {
                    if (type == 9) {
                        Jc = Jc.documentElement;
                    } else {
                        Jc = Jc.firstChild;
                    }
                    for (t = '', stack = [], i = 0; Jc;) {
                        do {
                            if (Jc.nodeType != 1) {
                                t += Jc.nodeValue;
                            }
                            stack[i++] = Jc;
                        } while ( Jc = Jc . firstChild );
                        while (i && !(Jc = stack[--i].nextSibling)) {}
                    }
                } else {
                    t = Jc.nodeValue;
                }
            }
            switch (Ic) {
            case 'number':
                return + t;
            case 'boolean':
                return !! t;
            default:
                return t;
            }
        },
        attrPropMap: {
            name: 'name',
            'class': 'className',
            dir: 'dir',
            id: 'id',
            name: 'name',
            title: 'title'
        },
        attrMatch: function(Kc, Lc, Mc) {
            if (!Lc || Mc == null && Kc.hasAttribute && Kc.hasAttribute(Lc) || Mc != null && Kc.getAttribute && Kc.getAttribute(Lc) == Mc) {
                return true;
            } else {
                return false;
            }
        },
        getDescendantNodes: function(Oc, Kc, Pc, Lc, Mc, Qc, Rc) {
            if (Qc) {
                Qc.delDescendant(Kc, Rc);
            }
            if (Mc && Lc == 'id' && Kc.getElementById) {
                Kc = Kc.getElementById(Mc);
                if (Kc && Oc.match(Kc)) {
                    Pc.push(Kc);
                }
            } else if (Mc && Lc == 'name' && Kc.getElementsByName) {
                var Wc = Kc.getElementsByName(Mc);
                for (var i = 0,
                l = Wc.length; i < l; i++) {
                    Kc = Wc[i];
                    if (Da.opera ? (Kc.name == Mc && Oc.match(Kc)) : Oc.match(Kc)) {
                        Pc.push(Kc);
                    }
                }
            } else if (Mc && Lc == 'class' && Kc.getElementsByClassName) {
                var Wc = Kc.getElementsByClassName(Mc);
                for (var i = 0,
                l = Wc.length; i < l; i++) {
                    Kc = Wc[i];
                    if (Kc.className == Mc && Oc.match(Kc)) {
                        Pc.push(Kc);
                    }
                }
            } else if (Oc.notOnlyElement) { (function(Xc) {
                    var f = arguments.callee;
                    for (var Kc = Xc.firstChild; Kc; Kc = Kc.nextSibling) {
                        if (wa.attrMatch(Kc, Lc, Mc)) {
                            if (Oc.match(Kc.nodeType)) Pc.push(Kc);
                        }
                        f(Kc);
                    }
                })(Kc);
            } else {
                var Tc = Oc.name;
                if (Kc.getElementsByTagName) {
                    var Wc = Kc.getElementsByTagName(Tc);
                    if (Wc) {
                        var i = 0;
                        while (Kc = Wc[i++]) {
                            if (wa.attrMatch(Kc, Lc, Mc)) Pc.push(Kc);
                        }
                    }
                }
            }
            return Pc;
        },
        getChildNodes: function(Yc, Kc, Zc, Lc, Mc) {
            for (var Kc = Kc.firstChild; Kc; Kc = Kc.nextSibling) {
                if (wa.attrMatch(Kc, Lc, Mc)) {
                    if (Yc.match(Kc)) Zc.push(Kc);
                }
            }
            return Zc;
        }
    };
    
    if (!window.Step && window.defaultConfig) window.Step = null;
    za = function(gd, hd) {
        this.axis = gd;
        this.reverse = za.axises[gd][0];
        this.func = za.axises[gd][1];
        this.test = hd;
        this.predicates = [];
        this._quickAttr = za.axises[gd][2]
    };
    za.axises = {
        ancestor: [true,
        function(jd, kd, ld, _, md, od, pd) {
            while (kd = kd.parentNode) {
                if (od && kd.nodeType == 1) {
                    od.reserveDelByNode(kd, pd, true);
                }
                if (jd.match(kd)) ld.unshift(kd);
            }
            return ld;
        }],
        'ancestor-or-self': [true,
        function(qd, rd, sd, _, td, ud, vd) {
            do {
                if (ud && rd.nodeType == 1) {
                    ud.reserveDelByNode(rd, vd, true);
                }
                if (qd.match(rd)) sd.unshift(rd);
            } while ( rd = rd . parentNode ) return sd;
        }],
        attribute: [false,
        function(wd, xd, yd) {
            var zd = xd.attributes;
            if (zd) {
                if ((wd.notOnlyElement && wd.type == 0) || wd.name == '*') {
                    for (var i = 0,
                    attr; attr = zd[i]; i++) {
                        yd.push(attr);
                    }
                } else {
                    var Bd = zd.getNamedItem(wd.name);
                    if (Bd) {
                        yd.push(Bd);
                    }
                }
            }
            return yd;
        }],
        child: [false, wa.getChildNodes, true],
        descendant: [false, wa.getDescendantNodes, true],
        'descendant-or-self': [false,
        function(wd, xd, yd, Cd, Dd, Ed, Fd) {
            if (wa.attrMatch(xd, Cd, Dd)) {
                if (wd.match(xd)) yd.push(xd);
            }
            return wa.getDescendantNodes(wd, xd, yd, Cd, Dd, Ed, Fd);
        },
        true],
        following: [false,
        function(wd, xd, yd, Gd, Hd) {
            do {
                var Id = xd;
                while (Id = Id.nextSibling) {
                    if (wa.attrMatch(Id, Gd, Hd)) {
                        if (wd.match(Id)) yd.push(Id);
                    }
                    yd = wa.getDescendantNodes(wd, Id, yd, Gd, Hd);
                }
            } while ( xd = xd . parentNode );
            return yd;
        },
        true],
        'following-sibling': [false,
        function(wd, xd, yd, _, Jd, Kd, Ld) {
            while (xd = xd.nextSibling) {
                if (Kd && xd.nodeType == 1) {
                    Kd.reserveDelByNode(xd, Ld);
                }
                if (wd.match(xd)) {
                    yd.push(xd);
                }
            }
            return yd;
        }],
        namespace: [false,
        function(wd, xd, yd) {
            return yd;
        }],
        parent: [false,
        function(wd, xd, yd) {
            if (xd.nodeType == 9) {
                return yd;
            }
            if (xd.nodeType == 2) {
                yd.push(xd.ownerElement);
                return yd;
            }
            var xd = xd.parentNode;
            if (wd.match(xd)) yd.push(xd);
            return yd;
        }],
        preceding: [true,
        function(wd, xd, yd, Md, Nd) {
            var Od = [];
            do {
                Od.unshift(xd);
            } while ( xd = xd . parentNode );
            for (var i = 1,
            l0 = Od.length; i < l0; i++) {
                var Pd = [];
                xd = Od[i];
                while (xd = xd.previousSibling) {
                    Pd.unshift(xd);
                }
                for (var j = 0,
                l1 = Pd.length; j < l1; j++) {
                    xd = Pd[j];
                    if (wa.attrMatch(xd, Md, Nd)) {
                        if (wd.match(xd)) yd.push(xd);
                    }
                    yd = wa.getDescendantNodes(wd, xd, yd, Md, Nd);
                }
            }
            return yd;
        },
        true],
        'preceding-sibling': [true,
        function(wd, xd, yd, _, Qd, Rd, Sd) {
            while (xd = xd.previousSibling) {
                if (Rd && xd.nodeType == 1) {
                    Rd.reserveDelByNode(xd, Sd, true);
                }
                if (wd.match(xd)) {
                    yd.unshift(xd)
                }
            }
            return yd;
        }],
        self: [false,
        function(wd, xd, yd) {
            if (wd.match(xd)) yd.push(xd);
            return yd;
        }]
    };
    za.parse = function(Td) {
        var Ud, test, step, token;
        if (Td.peek() == '.') {
            step = this.self();
            Td.next();
        } else if (Td.peek() == '..') {
            step = this.parent();
            Td.next();
        } else {
            if (Td.peek() == '@') {
                Ud = 'attribute';
                Td.next();
                if (Td.empty()) {
                    throw Error('missing attribute name');
                }
            } else {
                if (Td.peek(1) == '::') {
                    if (!/(?![0-9])[\w]/.test(Td.peek().charAt(0))) {
                        throw Error('bad token: ' + Td.next());
                    }
                    Ud = Td.next();
                    Td.next();
                    if (!this.axises[Ud]) {
                        throw Error('invalid axis: ' + Ud);
                    }
                    if (Td.empty()) {
                        throw Error('missing node name');
                    }
                } else {
                    Ud = 'child';
                }
            }
            token = Td.peek();
            if (!/(?![0-9])[\w]/.test(token.charAt(0))) {
                if (token == '*') {
                    test = sa.parse(Td)
                } else {
                    throw Error('bad token: ' + Td.next());
                }
            } else {
                if (Td.peek(1) == '(') {
                    if (!va.types[token]) {
                        throw Error('invalid node type: ' + token);
                    }
                    test = va.parse(Td)
                } else {
                    test = sa.parse(Td);
                }
            }
            step = new za(Ud, test);
        }
        Ta.parsePredicates(Td, step);
        return step;
    };
    za.self = function() {
        return new za('self', new va('node'));
    };
    za.parent = function() {
        return new za('parent', new va('node'));
    };
    za.prototype = new Ta();
    za.prototype.evaluate = function(Vd, Wd, Xd, Yd) {
        var Zd = Vd.node;
        var $d = false;
        if (!Wd && this.op == '//') {
            if (!this.needContextPosition && this.axis == 'child') {
                if (this.quickAttr) {
                    var ae = this.attrValueExpr ? this.attrValueExpr.string(Vd) : null;
                    var be = wa.getDescendantNodes(this.test, Zd, new ta(), this.attrName, ae, Xd, Yd);
                    be = this.evaluatePredicates(be, 1);
                } else {
                    var be = wa.getDescendantNodes(this.test, Zd, new ta(), null, null, Xd, Yd);
                    be = this.evaluatePredicates(be);
                }
            } else {
                var ce = new za('descendant-or-self', new va('node'));
                var de = ce.evaluate(Vd, false, Xd, Yd).list();
                var be = null;
                ce.op = '/';
                for (var i = 0,
                l = de.length; i < l; i++) {
                    if (!be) {
                        be = this.evaluate(new Ia(de[i]), true);
                    } else {
                        be.merge(this.evaluate(new Ia(de[i]), true));
                    }
                }
                be = be || new ta();
            }
        } else {
            if (this.needContextPosition) {
                Xd = null;
                Yd = null;
            }
            if (this.quickAttr) {
                var ae = this.attrValueExpr ? this.attrValueExpr.string(Vd) : null;
                var be = this.func(this.test, Zd, new ta(), this.attrName, ae, Xd, Yd);
                be = this.evaluatePredicates(be, 1);
            } else {
                var be = this.func(this.test, Zd, new ta(), null, null, Xd, Yd);
                be = this.evaluatePredicates(be);
            }
            if (Xd) {
                Xd.doDel();
            }
        }
        return be;
    };
    za.prototype.predicate = function(ee) {
        this.predicates.push(ee);
        if (ee.needContextPosition || ee.datatype == 'number' || ee.datatype == 'void') {
            this.needContextPosition = true;
        }
        if (this._quickAttr && this.predicates.length == 1 && ee.quickAttr) {
            var fe = ee.attrName;
            this.attrName = fe;
            this.attrValueExpr = ee.attrValueExpr;
            this.quickAttr = true;
        }
    };
    za.prototype.show = function(ge) {
        ge = ge || '';
        var t = '';
        t += ge + 'step: ' + '\\n';
        ge += '    ';
        if (this.axis) t += ge + 'axis: ' + this.axis + '\\n';
        t += this.test.show(ge);
        if (this.predicates.length) {
            t += ge + 'predicates: ' + '\\n';
            ge += '    ';
            for (var i = 0; i < this.predicates.length; i++) {
                t += this.predicates[i].show(ge);
            }
        }
        return t;
    };
    if (!window.NodeType && window.defaultConfig) window.NodeType = null;
    va = function(he, je) {
        this.name = he;
        this.literal = je;
        switch (he) {
        case 'comment':
            this.type = 8;
            break;
        case 'text':
            this.type = 3;
            break;
        case 'processing-instruction':
            this.type = 7;
            break;
        case 'node':
            this.type = 0;
            break;
        }
    };
    va.types = {
        'comment': 1,
        'text': 1,
        'processing-instruction': 1,
        'node': 1
    };
    va.parse = function(ke) {
        var le, literal, ch;
        le = ke.next();
        ke.next();
        if (ke.empty()) {
            throw Error('bad nodetype');
        }
        ch = ke.peek().charAt(0);
        if (ch == '"' || ch == "'") {
            literal = ra.parse(ke);
        }
        if (ke.empty()) {
            throw Error('bad nodetype');
        }
        if (ke.next() != ')') {
            ke.back();
            throw Error('bad token ' + ke.next());
        }
        return new va(le, literal);
    };
    va.prototype = new Ma();
    va.prototype.notOnlyElement = true;
    va.prototype.match = function(me) {
        return ! this.type || this.type == me.nodeType;
    };
    va.prototype.show = function(ne) {
        ne = ne || '';
        var t = '';
        t += ne + 'nodetype: ' + this.type + '\\n';
        if (this.literal) {
            ne += '    ';
            t += this.literal.show(ne);
        }
        return t;
    };
    if (!window.NameTest && window.defaultConfig) window.NameTest = null;
    sa = function(oe) {
        this.name = oe.toLowerCase();
    };
    sa.parse = function(pe) {
        if (pe.peek() != '*' && pe.peek(1) == ':' && pe.peek(2) == '*') {
            return new sa(pe.next() + pe.next() + pe.next());
        }
        return new sa(pe.next());
    };
    sa.prototype = new Ma();
    sa.prototype.match = function(qe) {
        var re = qe.nodeType;
        if (re == 1 || re == 2) {
            if (this.name == '*' || this.name == qe.nodeName.toLowerCase()) {
                return true;
            }
        }
        return false;
    };
    sa.prototype.show = function(se) {
        se = se || '';
        var t = '';
        t += se + 'nametest: ' + this.name + '\\n';
        return t;
    };
    if (!window.VariableReference && window.defaultConfig) window.VariableReference = null;
    Ca = function(te) {
        this.name = te.substring(1);
    };
    Ca.parse = function(ue) {
        var ve = ue.next();
        if (ve.length < 2) {
            throw Error('unnamed variable reference');
        }
        return new Ca(ve)
    };
    Ca.prototype = new Ma();
    Ca.prototype.datatype = 'void';
    Ca.prototype.show = function(we) {
        we = we || '';
        var t = '';
        t += we + 'variable: ' + this.name + '\\n';
        return t;
    };
    if (!window.Literal && window.defaultConfig) window.Literal = null;
    ra = function(xe) {
        this.text = xe.substring(1, xe.length - 1);
    };
    ra.parse = function(ye) {
        var ze = ye.next();
        if (ze.length < 2) {
            throw Error('unclosed literal string');
        }
        return new ra(ze)
    };
    ra.prototype = new Ma();
    ra.prototype.datatype = 'string';
    ra.prototype.evaluate = function(Ae) {
        return this.text;
    };
    ra.prototype.show = function(Be) {
        Be = Be || '';
        var t = '';
        t += Be + 'literal: ' + this.text + '\\n';
        return t;
    };
    if (!window.Number && window.defaultConfig) window.Number = null;
    xa = function(Ce) {
        this.digit = +Ce;
    };
    xa.parse = function(De) {
        return new xa(De.next());
    };
    xa.prototype = new Ma();
    xa.prototype.datatype = 'number';
    xa.prototype.evaluate = function(Ee) {
        return this.digit;
    };
    xa.prototype.show = function(Fe) {
        Fe = Fe || '';
        var t = '';
        t += Fe + 'number: ' + this.digit + '\\n';
        return t;
    };
    if (!window.FunctionCall && window.defaultConfig) window.FunctionCall = null;
    qa = function(Ge) {
        var He = qa.funcs[Ge];
        if (!He) throw Error(Ge + ' is not a function');
        this.name = Ge;
        this.func = He[0];
        this.args = [];
        this.datatype = He[1];
        if (He[2]) {
            this.needContextPosition = true;
        }
        this.needContextNodeInfo = He[3];
        this.needContextNode = this.needContextNodeInfo[0]
    };
    qa.funcs = {
        'context-node': [function() {
            if (arguments.length != 0) {
                throw Error('Function context-node expects ()');
            }
            var ns;
            ns = new ta();
            ns.push(this.node);
            return ns;
        },
        'nodeset', false, [true]],
        'root-node': [function() {
            if (arguments.length != 0) {
                throw Error('Function root-node expects ()');
            }
            var ns, ctxn;
            ns = new ta();
            ctxn = this.node;
            if (ctxn.nodeType == 9) ns.push(ctxn);
            else ns.push(ctxn.ownerDocument);
            return ns;
        },
        'nodeset', false, []],
        last: [function() {
            if (arguments.length != 0) {
                throw Error('Function last expects ()');
            }
            return this.last;
        },
        'number', true, []],
        position: [function() {
            if (arguments.length != 0) {
                throw Error('Function position expects ()');
            }
            return this.position;
        },
        'number', true, []],
        count: [function(ns) {
            if (arguments.length != 1 || !(ns = ns.evaluate(this)).isNodeSet) {
                throw Error('Function count expects (nodeset)');
            }
            return ns.length;
        },
        'number', false, []],
        id: [function(s) {
            var Ie, ns, i, id, elm, ctxn, doc;
            if (arguments.length != 1) {
                throw Error('Function id expects (object)');
            }
            ctxn = this.node;
            if (ctxn.nodeType == 9) doc = ctxn;
            else doc = ctxn.ownerDocument;
            s = s.string(this);
            Ie = s.split(/\s+/);
            ns = new ta();
            for (i = 0, l = Ie.length; i < l; i++) {
                id = Ie[i];
                elm = doc.getElementById(id);
                if (Da.opera && elm && elm.id != id) {
                    var Je = doc.getElementsByName(id);
                    for (var j = 0,
                    l0 = Je.length; j < l0; j++) {
                        elm = Je[j];
                        if (elm.id == id) {
                            ns.push(elm);
                        }
                    }
                } else {
                    if (elm) ns.push(elm)
                }
            }
            ns.isSorted = false;
            return ns;
        },
        'nodeset', false, []],
        'local-name': [function(ns) {
            var nd;
            switch (arguments.length) {
            case 0:
                nd = this.node;
                break;
            case 1:
                if ((ns = ns.evaluate(this)).isNodeSet) {
                    nd = ns.first();
                    break;
                }
            default:
                throw Error('Function local-name expects (nodeset?)');
                break;
            }
            return '' + nd.nodeName.toLowerCase();
        },
        'string', false, [true, false]],
        name: [function(ns) {
            return qa.funcs['local-name'][0].apply(this, arguments);
        },
        'string', false, [true, false]],
        'namespace-uri': [function(ns) {
            return '';
        },
        'string', false, [true, false]],
        string: [function(s) {
            switch (arguments.length) {
            case 0:
                s = wa.to('string', this.node);
                break;
            case 1:
                s = s.string(this);
                break;
            default:
                throw Error('Function string expects (object?)');
                break;
            }
            return s;
        },
        'string', false, [true, false]],
        concat: [function(s1, s2) {
            if (arguments.length < 2) {
                throw Error('Function concat expects (string, string[, ...])');
            }
            for (var t = '',
            i = 0,
            l = arguments.length; i < l; i++) {
                t += arguments[i].string(this);
            }
            return t;
        },
        'string', false, []],
        'starts-with': [function(s1, s2) {
            if (arguments.length != 2) {
                throw Error('Function starts-with expects (string, string)');
            }
            s1 = s1.string(this);
            s2 = s2.string(this);
            return s1.indexOf(s2) == 0;
        },
        'boolean', false, []],
        contains: [function(s1, s2) {
            if (arguments.length != 2) {
                throw Error('Function contains expects (string, string)');
            }
            s1 = s1.string(this);
            s2 = s2.string(this);
            return s1.indexOf(s2) != -1;
        },
        'boolean', false, []],
        substring: [function(s, n1, n2) {
            var a1, a2;
            s = s.string(this);
            n1 = n1.number(this);
            switch (arguments.length) {
            case 2:
                n2 = s.length - n1 + 1;
                break;
            case 3:
                n2 = n2.number(this);
                break;
            default:
                throw Error('Function substring expects (string, string)');
                break;
            }
            n1 = Math.round(n1);
            n2 = Math.round(n2);
            a1 = n1 - 1;
            a2 = n1 + n2 - 1;
            if (a2 == Infinity) {
                return s.substring(a1 < 0 ? 0 : a1);
            } else {
                return s.substring(a1 < 0 ? 0 : a1, a2)
            }
        },
        'string', false, []],
        'substring-before': [function(s1, s2) {
            var n;
            if (arguments.length != 2) {
                throw Error('Function substring-before expects (string, string)');
            }
            s1 = s1.string(this);
            s2 = s2.string(this);
            n = s1.indexOf(s2);
            if (n == -1) return '';
            return s1.substring(0, n);
        },
        'string', false, []],
        'substring-after': [function(s1, s2) {
            if (arguments.length != 2) {
                throw Error('Function substring-after expects (string, string)');
            }
            s1 = s1.string(this);
            s2 = s2.string(this);
            var n = s1.indexOf(s2);
            if (n == -1) return '';
            return s1.substring(n + s2.length);
        },
        'string', false, []],
        'string-length': [function(s) {
            switch (arguments.length) {
            case 0:
                s = wa.to('string', this.node);
                break;
            case 1:
                s = s.string(this);
                break;
            default:
                throw Error('Function string-length expects (string?)');
                break;
            }
            return s.length;
        },
        'number', false, [true, false]],
        'normalize-space': [function(s) {
            switch (arguments.length) {
            case 0:
                s = wa.to('string', this.node);
                break;
            case 1:
                s = s.string(this);
                break;
            default:
                throw Error('Function normalize-space expects (string?)');
                break;
            }
            return s.replace(/\s+/g, ' ').replace(/^ /, '').replace(/ $/, '');
        },
        'string', false, [true, false]],
        translate: [function(s1, s2, s3) {
            if (arguments.length != 3) {
                throw Error('Function translate expects (string, string, string)');
            }
            s1 = s1.string(this);
            s2 = s2.string(this);
            s3 = s3.string(this);
            var Le = [];
            for (var i = 0,
            l = s2.length; i < l; i++) {
                var ch = s2.charAt(i);
                if (!Le[ch]) Le[ch] = s3.charAt(i) || '';
            }
            for (var t = '',
            i = 0,
            l = s1.length; i < l; i++) {
                var ch = s1.charAt(i);
                var Me = Le[ch];
                t += (Me != ca) ? Me: ch;
            }
            return t;
        },
        'string', false, []],
        'boolean': [function(b) {
            if (arguments.length != 1) {
                throw Error('Function boolean expects (object)');
            }
            return b.bool(this)
        },
        'boolean', false, []],
        not: [function(b) {
            if (arguments.length != 1) {
                throw Error('Function not expects (object)');
            }
            return ! b.bool(this)
        },
        'boolean', false, []],
        'true': [function() {
            if (arguments.length != 0) {
                throw Error('Function true expects ()');
            }
            return true;
        },
        'boolean', false, []],
        'false': [function() {
            if (arguments.length != 0) {
                throw Error('Function false expects ()');
            }
            return false;
        },
        'boolean', false, []],
        lang: [function(s) {
            return false;
        },
        'boolean', false, []],
        number: [function(n) {
            switch (arguments.length) {
            case 0:
                n = wa.to('number', this.node);
                break;
            case 1:
                n = n.number(this);
                break;
            default:
                throw Error('Function number expects (object?)');
                break;
            }
            return n;
        },
        'number', false, [true, false]],
        sum: [function(ns) {
            var Ne, n, i, l;
            if (arguments.length != 1 || !(ns = ns.evaluate(this)).isNodeSet) {
                throw Error('Function sum expects (nodeset)');
            }
            Ne = ns.list();
            n = 0;
            for (i = 0, l = Ne.length; i < l; i++) {
                n += wa.to('number', Ne[i]);
            }
            return n;
        },
        'number', false, []],
        floor: [function(n) {
            if (arguments.length != 1) {
                throw Error('Function floor expects (number)');
            }
            n = n.number(this);
            return Math.floor(n);
        },
        'number', false, []],
        ceiling: [function(n) {
            if (arguments.length != 1) {
                throw Error('Function ceiling expects (number)');
            }
            n = n.number(this);
            return Math.ceil(n);
        },
        'number', false, []],
        round: [function(n) {
            if (arguments.length != 1) {
                throw Error('Function round expects (number)');
            }
            n = n.number(this);
            return Math.round(n);
        },
        'number', false, []]
    };
    qa.parse = function(Oe) {
        var Pe, func = new qa(Oe.next());
        Oe.next();
        while (Oe.peek() != ')') {
            if (Oe.empty()) {
                throw Error('missing function argument list');
            }
            Pe = oa.parse(Oe);
            func.arg(Pe);
            if (Oe.peek() != ',') break;
            Oe.next();
        }
        if (Oe.empty()) {
            throw Error('unclosed function argument list');
        }
        if (Oe.next() != ')') {
            Oe.back();
            throw Error('bad token: ' + Oe.next());
        }
        return func
    };
    qa.prototype = new Ma();
    qa.prototype.evaluate = function(Qe) {
        return this.func.apply(Qe, this.args);
    };
    qa.prototype.arg = function(Re) {
        this.args.push(Re);
        if (Re.needContextPosition) {
            this.needContextPosition = true;
        }
        var Se = this.args;
        if (Re.needContextNode) {
            Se.needContexNode = true;
        }
        this.needContextNode = Se.needContextNode || this.needContextNodeInfo[Se.length];
    };
    qa.prototype.show = function(Te) {
        Te = Te || '';
        var t = '';
        t += Te + 'function: ' + this.name + '\\n';
        Te += '    ';
        if (this.args.length) {
            t += Te + 'arguments: ' + '\\n';
            Te += '    ';
            for (var i = 0; i < this.args.length; i++) {
                t += this.args[i].show(Te);
            }
        }
        return t;
    };
    var Ze = {
        uuid: 1,
        get: function($e) {
            return $e.__ba || ($e.__ba = this.uuid++);
        }
    };

    if (!window.NodeSet && window.defaultConfig) window.NodeSet = null;
    ta = function() {
        this.length = 0;
        this.nodes = [];
        this.seen = {};
        this.idIndexMap = null;
        this.reserveDels = [];
    };
    ta.prototype.isNodeSet = true;
    ta.prototype.isSorted = true;
    ta.prototype.merge = function(af) {
        this.isSorted = false;
        if (af.only) {
            return this.push(af.only);
        }
        if (this.only) {
            var bf = this.only;
            delete this.only;
            this.push(bf);
            this.length--;
        }
        var cf = af.nodes;
        for (var i = 0,
        l = cf.length; i < l; i++) {
            this._add(cf[i]);
        }
    };
    ta.prototype.sort = function() {
        if (this.only) return;
        if (this.sortOff) return;
        if (!this.isSorted) {
            this.isSorted = true;
            this.idIndexMap = null;
            var ef = this.nodes;
            ef.sort(function(a, b) {
                if (a == b) return 0;
                if (a.compareDocumentPosition) {
                    var ff = a.compareDocumentPosition(b);
                    if (ff & 2) return 1;
                    if (ff & 4) return - 1;
                    return 0;
                } else {
                    var gf = a,
                    node2 = b,
                    ancestor1 = a,
                    ancestor2 = b,
                    deep1 = 0,
                    deep2 = 0;
                    while (ancestor1 = ancestor1.parentNode) deep1++;
                    while (ancestor2 = ancestor2.parentNode) deep2++;
                    if (deep1 > deep2) {
                        while (deep1--!=deep2) gf = gf.parentNode;
                        if (gf == node2) return 1;
                    } else if (deep2 > deep1) {
                        while (deep2--!=deep1) node2 = node2.parentNode;
                        if (gf == node2) return - 1;
                    }
                    while ((ancestor1 = gf.parentNode) != (ancestor2 = node2.parentNode)) {
                        gf = ancestor1;
                        node2 = ancestor2;
                    }
                    while (gf = gf.nextSibling) if (gf == node2) return - 1;
                    return 1;
                }
            });
        }
    };

    ta.prototype.reserveDelByNodeID = function(id, rf, sf) {
        var tf = this.createIdIndexMap();
        var uf;
        if (uf = tf[id]) {
            if (sf && (this.length - rf - 1) > uf || !sf && rf < uf) {
                var vf = {
                    value: uf,
                    order: String.fromCharCode(uf),
                    toString: function() {
                        return this.order
                    },
                    valueOf: function() {
                        return this.value
                    }
                };
                this.reserveDels.push(vf);
            }
        }
    };

    ta.prototype.reserveDelByNode = function(wf, xf, yf) {
        this.reserveDelByNodeID(Ze.get(wf), xf, yf);

    };
    ta.prototype.doDel = function() {
        if (!this.reserveDels.length) return;
        if (this.length < 0x10000) {
            var zf = this.reserveDels.sort(function(a, b) {
                return b - a
            });
        } else {
            var zf = this.reserveDels.sort(function(a, b) {
                return b - a
            });
        }
        for (var i = 0,
        l = zf.length; i < l; i++) {
            this.del(zf[i]);
        }
        this.reserveDels = [];
        this.idIndexMap = null;
    };
    ta.prototype.createIdIndexMap = function() {
        if (this.idIndexMap) {
            return this.idIndexMap;
        } else {
            var Af = this.idIndexMap = {};
            var Bf = this.nodes;
            for (var i = 0,
            l = Bf.length; i < l; i++) {
                var Cf = Bf[i];
                var id = Ze.get(Cf);
                Af[id] = i;
            }
            return Af;
        }
    };
    ta.prototype.del = function(Ff) {
        this.length--;
        if (this.only) {
            delete this.only;
        } else {
            var Gf = this.nodes.splice(Ff, 1)[0];
            if (this._first == Gf) {
                delete this._first;
                delete this._firstSourceIndex;
                delete this._firstSubIndex;
            }
            delete this.seen[Ze.get(Gf)];
        }
    };
    ta.prototype.delDescendant = function(Hf, If) {
        if (this.only) return;
        var Jf = Hf.nodeType;
        if (Jf != 1 && Jf != 9) return;
        if (Da.applewebkit2) return;
        if (!Hf.contains) {
            if (Jf == 1) {
                var Kf = Hf;
                Hf = {
                    contains: function(Lf) {
                        return Lf.compareDocumentPosition(Kf) & 8;
                    }
                };
            } else {
                Hf = {
                    contains: function() {
                        return true;
                    }
                };
            }
        }
        var Mf = this.nodes;
        for (var i = If + 1; i < Mf.length; i++) {
            if (Hf.contains(Mf[i])) {
                this.del(i);
                i--;
            }
        }
    };
    ta.prototype._add = function(Nf, Of) {
        var Qf = this.seen;
        var id = Ze.get(Nf);
        if (Qf[id]) return true;
        Qf[id] = true;
        this.length++;
        if (Of) this.nodes.unshift(Nf);
        else this.nodes.push(Nf);
    };
    ta.prototype.unshift = function(Rf) {
        if (!this.length) {
            this.length++;
            this.only = Rf;
            return
        }
        if (this.only) {
            var Sf = this.only;
            delete this.only;
            this.unshift(Sf);
            this.length--;
        }
        return this._add(Rf, true);
    };
    ta.prototype.push = function(Tf) {
        if (!this.length) {
            this.length++;
            this.only = Tf;
            return;
        }
        if (this.only) {
            var Uf = this.only;
            delete this.only;
            this.push(Uf);
            this.length--;
        }
        return this._add(Tf);
    };
    ta.prototype.first = function() {
        if (this.only) return this.only;
        if (this.nodes.length > 1) this.sort();
        return this.nodes[0];
    };
    ta.prototype.list = function() {
        if (this.only) return [this.only];
        this.sort();
        return this.nodes;
    };
    ta.prototype.string = function() {
        var Wf = this.only || this.first();
        return Wf ? wa.to('string', Wf) : '';
    };
    ta.prototype.bool = function() {
        return !! (this.length || this.only);
    };
    ta.prototype.number = function() {
        return + this.string();
    };
    ta.prototype.iterator = function(Xf) {
        this.sort();
        var Yf = this;
        if (!Xf) {
            var Zf = 0;
            return function() {
                if (Yf.only && Zf++==0) return Yf.only;
                return Yf.nodes[Zf++];
            };
        } else {
            var Zf = 0;
            return function() {
                var ag = Yf.length - (Zf++) - 1;
                if (Yf.only && ag == 0) return Yf.only;
                return Yf.nodes[ag];
            };
        }
    };
    var cg = function(dg) {
        dg = dg || this;
        var eg = dg.document;
        var ca = dg.undefined;
        dg.XPathExpression = function(fg) {
            if (!fg.length) {
                throw dg.Error('no expression');
            }
            var gg = this.lexer = Ea(fg);
            if (gg.empty()) {
                throw dg.Error('no expression');
            }
            this.expr = oa.parse(gg);
            if (!gg.empty()) {
                throw dg.Error('bad token: ' + gg.next());
            }
        };
        dg.XPathExpression.prototype.evaluate = function(hg, ig) {
            return new dg.XPathResult(this.expr.evaluate(new Ia(hg)), ig);
        };
        dg.XPathResult = function(jg, kg) {
            if (kg == 0) {
                switch (typeof jg) {
                case 'object':
                    kg++;
                case 'boolean':
                    kg++;
                case 'string':
                    kg++;
                case 'number':
                    kg++;
                }
            }
            this.resultType = kg;
            switch (kg) {
            case 1:
                this.numberValue = jg.isNodeSet ? jg.number() : +jg;
                return;
            case 2:
                this.stringValue = jg.isNodeSet ? jg.string() : '' + jg;
                return;
            case 3:
                this.booleanValue = jg.isNodeSet ? jg.bool() : !!jg;
                return;
            case 4:
            case 5:
            case 6:
            case 7:
                this.nodes = jg.list();
                this.snapshotLength = jg.length;
                this.index = 0;
                this.invalidIteratorState = false;
                break;
            case 8:
            case 9:
                this.singleNodeValue = jg.first();
                return;
            }
        };
        dg.XPathResult.prototype.iterateNext = function() {
            return this.nodes[this.index++]
        };
        dg.XPathResult.prototype.snapshotItem = function(i) {
            return this.nodes[i]
        };
        dg.XPathResult.ANY_TYPE = 0;
        dg.XPathResult.NUMBER_TYPE = 1;
        dg.XPathResult.STRING_TYPE = 2;
        dg.XPathResult.BOOLEAN_TYPE = 3;
        dg.XPathResult.UNORDERED_NODE_ITERATOR_TYPE = 4;
        dg.XPathResult.ORDERED_NODE_ITERATOR_TYPE = 5;
        dg.XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE = 6;
        dg.XPathResult.ORDERED_NODE_SNAPSHOT_TYPE = 7;
        dg.XPathResult.ANY_UNORDERED_NODE_TYPE = 8;
        dg.XPathResult.FIRST_ORDERED_NODE_TYPE = 9;
        eg.createExpression = function(lg) {
            return new dg.XPathExpression(lg, null);
        };
        eg.evaluate = function(mg, ng, _, og) {
            return eg.createExpression(mg, null).evaluate(ng, og);
        };
    };
    var pg;
    if (ea.targetFrame) {
        var qg = document.getElementById(ea.targetFrame);
        if (qg) pg = qg.contentWindow;
    }
    if (ea.exportInstaller) {
        window.install = cg;
    }
    if (!ea.hasNative || !ea.useNative) {
        cg(pg || window);
    }
})();
window.install();
'''



try:
    from qt4w.webdriver.webkitwebdriver import WebkitWebDriver
    from qt4w.util import JavaScriptError
    from qt4a.androiddriver.util import AndroidSpyError
    class AndroidWebDriver(WebkitWebDriver):
        '''Android中的WebDriver
        '''
        
        def __init__(self, webview):
            super(AndroidWebDriver, self).__init__(webview)
            self._usb_xpath_lib = False
            
        def eval_script(self, frame_xpaths, script):
            '''在指定frame中执行JavaScript，并返回执行结果（该实现需要处理js基础库未注入情况的处理）
            
            :param frame_xpaths: frame元素的XPATH路径，如果是顶层页面，怎传入“[]”
            :type frame_xpaths:  list
            :param script:       要执行的JavaScript语句
            :type script:        string
            '''
            try:
                return super(AndroidWebDriver, self).eval_script(frame_xpaths, script)
            except JavaScriptError as e:
                err_msg = e.message
                err_msg = err_msg.split('\n')[0]
                if 'INVALID_EXPRESSION_ERR: DOM XPath Exception 51' in err_msg:
                    # http://stackoverflow.com/questions/21472896/android-4-3-default-browser-xmldoc-evaluate-throws-invalid-expression-err-dom
                    # 可能是三星手机的bug，需要使用其它的XPath库
                    self.eval_script(frame_xpaths, xpath_lib_str)
                    self._usb_xpath_lib = True
                    return self.eval_script(frame_xpaths, script)
                elif 'Result Error:' in err_msg:
                    # 执行js超时，重试
                    time.sleep(5)
                    return self.eval_script(frame_xpaths, script)
                else:
                    raise e
            except AndroidSpyError as e:
                if 'java.lang.RuntimeException: Result Error:' in e.message:
                    # 一般是页面未加载完成，等待重试
                    time.sleep(2)
                    return self.eval_script(frame_xpaths, script)
                
except ImportError:
    pass


if __name__ == '__main__':
    pass
