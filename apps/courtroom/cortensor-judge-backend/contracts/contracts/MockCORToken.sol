// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MockCORToken
 * @dev Mock ERC-20 token for local testing of Cortensor Judge
 * This is ONLY for development/testing. Replace with real $COR token in production.
 */

contract MockCORToken {
    string public constant name = "Cortensor Reputation Token";
    string public constant symbol = "COR";
    uint8 public constant decimals = 18;
    uint256 public totalSupply;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    constructor() {
        // No initial supply, mint as needed
    }

    /**
     * @dev Mint new tokens (only for testing)
     */
    function mint(address to, uint256 amount) public {
        require(to != address(0), "Invalid address");
        require(amount > 0, "Invalid amount");
        
        balanceOf[to] += amount;
        totalSupply += amount;
        emit Transfer(address(0), to, amount);
    }

    /**
     * @dev Burn tokens
     */
    function burn(uint256 amount) public {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        
        balanceOf[msg.sender] -= amount;
        totalSupply -= amount;
        emit Transfer(msg.sender, address(0), amount);
    }

    /**
     * @dev Transfer tokens
     */
    function transfer(address to, uint256 amount) public returns (bool) {
        require(to != address(0), "Invalid address");
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    /**
     * @dev Transfer from one address to another
     */
    function transferFrom(
        address from,
        address to,
        uint256 amount
    ) public returns (bool) {
        require(from != address(0), "Invalid from address");
        require(to != address(0), "Invalid to address");
        require(balanceOf[from] >= amount, "Insufficient balance");
        require(allowance[from][msg.sender] >= amount, "Insufficient allowance");
        
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        allowance[from][msg.sender] -= amount;
        
        emit Transfer(from, to, amount);
        return true;
    }

    /**
     * @dev Approve tokens for spending
     */
    function approve(address spender, uint256 amount) public returns (bool) {
        require(spender != address(0), "Invalid spender");
        
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }
}
