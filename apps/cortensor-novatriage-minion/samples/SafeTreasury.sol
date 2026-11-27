// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// @title SafeTreasury - Clean check-effects-interactions fixture for contrast
contract SafeTreasury {
    address public immutable owner;
    mapping(address => uint256) public balances;
    bool private locked;

    error Unauthorized();
    error ReentrantCall();
    error TransferFailed();

    constructor() {
        owner = msg.sender;
    }

    modifier nonReentrant() {
        if (locked) revert ReentrantCall();
        locked = true;
        _;
        locked = false;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external nonReentrant {
        uint256 bal = balances[msg.sender];
        require(bal >= amount, "Insufficient");
        balances[msg.sender] = bal - amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        if (!ok) revert TransferFailed();
    }
}
