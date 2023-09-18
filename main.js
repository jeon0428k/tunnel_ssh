const {Tunnel} = require("./files/tunnel_v2");
const JSON5 = require("json5");
const fs = require("fs");

const DEFAULT_PATH = "config/config.json";

function tunnelStart(config) {
    const tunnel = new Tunnel(config);
    tunnel.start();
}

if (process.env.CONFIG) {
    const config = JSON.parse(process.env.CONFIG);
    tunnelStart(config);
}
else {
    const configs = JSON5.parse(fs.readFileSync(DEFAULT_PATH, 'utf8'));
    configs.map(config => {
        tunnelStart(config);
    });
}
