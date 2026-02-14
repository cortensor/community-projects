// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ICOR
 * @dev Interface for the COR token (ERC-20 compliant)
 * Represents the currency used in The Cortensor Judge for bonds, stakes, and rewards
 */
interface ICOR {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function totalSupply() external view returns (uint256);
    function decimals() external view returns (uint8);
    function name() external view returns (string memory);
    function symbol() external view returns (string memory);
}
