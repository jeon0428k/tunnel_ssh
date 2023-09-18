const { Client } = require('ssh2');
const net = require('net');

const config = {
    username: "ssh-username",
    password: "ssh-password",
    host: "ssh-server",
    port: 2585,
    srcHost: 'src-host',
    srcPort: 9091,
    dstHost: "dsc-host",
    dstPort: 8581,
    localHost: "127.0.0.1",
    localPort: 5555,
    keepaliveInterval : 10000,
};


let tunnel;
let remoteSocket;

function startTunnel() {
    tunnel = new Client();
    tunnel.on('ready', () => {
        createTunnel();
    });
    tunnel.on('error', (err) => {
        console.error('SSH connection error:', err);
        reconnect();
    });
    tunnel.on('end', () => {
        console.log('SSH connection closed');
        reconnect();
    });
    connect();
}

function connect() {
    console.log(`Connecting to SSH server ${config.host}:${config.port}`);
    try {
        const sshConfig = {
            host: config.host,
            port: config.port || 22, // 포트 옵션 추가
            username: config.username,
            password: config.password,
            keepaliveInterval: config.keepaliveInterval,
        }
        tunnel.connect(sshConfig);
        // setInterval(() => {
        //     if (!tunnel || !tunnel._sock || tunnel._sock.destroyed) {
        //         console.log('SSH connection lost. Reconnecting...');
        //         reconnect();
        //     } else if (!remoteSocket || remoteSocket.destroyed) {
        //         console.log('Remote socket connection lost. Reconnecting...');
        //         createTunnel();
        //     }
        // }, config.keepaliveInterval);
    } catch (err) {
        console.error('SSH connection error:', err);
        reconnect();
    }
}

function createTunnel() {
    tunnel.forwardOut(
        config.srcHost,
        config.srcPort,
        config.dstHost,
        config.dstPort,
        (err, stream) => {
            if (err) throw err;
            remoteSocket = net.createConnection(config.localPort, config.localHost, () => {
                console.log(`Remote socket connected to ${config.localHost}:${config.localPort}`);
                remoteSocket.pipe(stream).pipe(remoteSocket);
                remoteSocket.on('error', (error) => {
                    console.error('Remote socket error:', error);
                    reconnect();
                });
                remoteSocket.on('close', () => {
                    console.log('Remote socket closed');
                    reconnect();
                });
            });
        }
    );
}

function closeTunnel() {
    if (remoteSocket && !remoteSocket.destroyed) {
        remoteSocket.destroy(); // Remote socket 연결 종료
    }
    if (tunnel && !tunnel._sshstream._destroyed && !tunnel._sshstream._closing) {
        tunnel.end(); // SSH 터널 종료
    }
}

function reconnect() {
    closeTunnel();
    connect();
}

// 터널 시작
startTunnel();