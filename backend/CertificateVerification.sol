// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract CertificateVerification {
    struct Record {
        address issuer;
        uint256 timestamp;
    }

    mapping(bytes32 => Record) public records;

    event CertificateStored(bytes32 indexed hash, address issuer, uint256 timestamp);

    function store(bytes32 hash) external {
        require(records[hash].timestamp == 0, "already stored");
        records[hash] = Record({issuer: msg.sender, timestamp: block.timestamp});
        emit CertificateStored(hash, msg.sender, block.timestamp);
    }

    function exists(bytes32 hash) external view returns (bool) {
        return records[hash].timestamp != 0;
    }

    function get(bytes32 hash) external view returns (address issuer, uint256 timestamp) {
        Record memory r = records[hash];
        return (r.issuer, r.timestamp);
    }
}
