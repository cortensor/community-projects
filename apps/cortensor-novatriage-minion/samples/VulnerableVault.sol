// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title VulnerableVault - Intentional multi-issue fixture for NovaTriage Minion testing
contract VulnerableVault {
    address public owner;
    mapping(address => uint256) public balances;
    mapping(address => bool) public blacklisted;
    uint256 public totalSupply;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwnerTx() {
        require(tx.origin == owner, "Not owner");
        _;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(!blacklisted[msg.sender], "Blacklisted");
        require(balances[msg.sender] >= amount, "Insufficient");
        (bool ok, ) = msg.sender.call{value: amount}("");
        balances[msg.sender] -= amount;
    }

    function executeStrategy(address target, bytes calldata data) external onlyOwnerTx {
        target.delegatecall(data);
    }

    function setBlacklist(address user, bool blocked) external {
        blacklisted[user] = blocked;
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    function _mint(address to, uint256 amount) internal {
        balances[to] += amount;
        totalSupply += amount;
    }

    function emergencyWithdraw(address payable to) external onlyOwnerTx {
        to.call{value: address(this).balance}("");
    }
}
