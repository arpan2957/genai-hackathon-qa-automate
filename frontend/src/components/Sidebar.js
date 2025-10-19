import React, { useState } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import { LogoIcon, TestCaseIcon, SettingsIcon, SunIcon, MoonIcon, FolderIcon, DesktopIcon, DatabaseIcon } from './icons';

const Sidebar = ({ isPinned, isMobileOpen, setMobileOpen, uniqueProducts, selectedProduct, setSelectedProduct, isLoadingCases, currentPage, setCurrentPage }) => {
    const { theme, toggleTheme } = useTheme();
    const [isHovering, setHovering] = useState(false);
    const isExpanded = isPinned || isHovering;
    
    // Responsive icon sizing based on sidebar state
    const iconSize = isExpanded ? '28px' : '20px';

    const ExpandingText = ({ children }) => (
        <span className={`ml-2 whitespace-nowrap overflow-hidden transition-all duration-200 ${isExpanded ? 'max-w-36 opacity-100' : 'max-w-0 opacity-0'}`}>
            {children}
        </span>
    );

    const NavLink = ({ icon, children, onClick, isActive }) => (
        <li>
            <button
                onClick={onClick}
                className={`flex items-center w-full pl-3 pr-1 py-3 text-sm font-medium rounded-lg transition-colors text-left
                    ${isActive ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white'}
                `}
            >
                {React.cloneElement(icon, {
                    style: {
                        width: iconSize,
                        height: iconSize,
                        minWidth: iconSize,
                        minHeight: iconSize,
                        transition: 'all 0.3s ease',
                        flexShrink: 0
                    }
                })}
                <ExpandingText>{children}</ExpandingText>
            </button>
        </li>
    );

    const ProductsNavLink = ({ icon, children, uniqueProducts, selectedProduct, setSelectedProduct, isLoadingCases }) => {
        const [isProductsExpanded, setProductsExpanded] = useState(true);

        return (
            <>
                <li>
                    <button
                        onClick={() => setProductsExpanded(!isProductsExpanded)}
                        className={`flex items-center w-full pl-3 pr-1 py-3 text-sm font-medium rounded-lg transition-colors text-left
                            ${isProductsExpanded ? 'text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white'}
                        `}
                    >
                        {React.cloneElement(icon, {
                            style: {
                                width: iconSize,
                                height: iconSize,
                                minWidth: iconSize,
                                minHeight: iconSize,
                                transition: 'all 0.3s ease',
                                flexShrink: 0
                            }
                        })}
                        <ExpandingText>{children}</ExpandingText>
                        {isExpanded && (
                            <svg className={`w-4 h-4 ml-auto transition-transform ${isProductsExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
                        )}
                    </button>
                </li>
                {isProductsExpanded && isExpanded && (
                    isLoadingCases ? (
                        <li className="pl-8 pr-1 py-2 text-sm text-gray-400 dark:text-gray-500">
                            Loading...
                        </li>
                    ) : uniqueProducts.length > 0 ? (
                        uniqueProducts.map(productName => (
                            <NavLink
                                key={productName}
                                onClick={() => setSelectedProduct(productName)}
                                isActive={selectedProduct === productName}
                                icon={<span className="w-5 h-5 min-w-5 min-h-5"></span>}
                            >
                                {productName}
                            </NavLink>
                        ))
                    ) : (
                        <li className="pl-8 pr-1 py-2 text-sm text-gray-400 dark:text-gray-500">
                            No products found
                        </li>
                    )
                )}
            </>
        );
    };

    const sidebarContent = (
        <div className="flex flex-col h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800"
             onMouseEnter={() => !isPinned && setHovering(true)}
             onMouseLeave={() => !isPinned && setHovering(false)}>
            <div className="flex items-center pl-3 pr-1 py-4 h-16 border-b border-gray-200 dark:border-gray-800">
                    <LogoIcon 
                        className="text-cyan-600" 
                        style={{ 
                            width: iconSize, 
                            height: iconSize,
                            minWidth: iconSize,
                            minHeight: iconSize,
                            transition: 'all 0.3s ease',
                            flexShrink: 0
                        }}
                    />
                    <span className={`ml-1 text-xl font-bold text-gray-800 dark:text-white whitespace-nowrap overflow-hidden transition-all duration-200 ${isExpanded ? 'max-w-44 opacity-100' : 'max-w-0 opacity-0'}`}>
                        QA Automate
                    </span>
            </div>
            <ul className="flex-1 pl-3 pr-1 py-4 space-y-2">
                <NavLink icon={<TestCaseIcon />} onClick={() => {setSelectedProduct(null); setCurrentPage('testcases');}} isActive={selectedProduct === null && currentPage === 'testcases'}>All Test Cases</NavLink>

                <ProductsNavLink
                    icon={<FolderIcon />}
                    uniqueProducts={uniqueProducts}
                    selectedProduct={selectedProduct}
                    setSelectedProduct={setSelectedProduct}
                    isLoadingCases={isLoadingCases}
                >
                    Products
                </ProductsNavLink>

                <NavLink icon={<DatabaseIcon />} onClick={() => setCurrentPage('knowledgebase')} isActive={currentPage === 'knowledgebase'}>Knowledge Base</NavLink>

                <NavLink icon={<SettingsIcon />}>Settings</NavLink>
            </ul>
            <div className="pl-3 pr-1 py-4 border-t border-gray-200 dark:border-gray-800">
                <button onClick={toggleTheme} className="flex items-center w-full pl-3 pr-1 py-3 text-sm font-medium rounded-lg text-gray-500 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white">
                    {theme === 'light' ? (
                        <SunIcon 
                            style={{ 
                                width: iconSize, 
                                height: iconSize,
                                minWidth: iconSize,
                                minHeight: iconSize,
                                transition: 'all 0.3s ease',
                                flexShrink: 0
                            }}
                        />
                    ) : theme === 'dark' ? (
                        <MoonIcon 
                            style={{ 
                                width: iconSize, 
                                height: iconSize,
                                minWidth: iconSize,
                                minHeight: iconSize,
                                transition: 'all 0.3s ease',
                                flexShrink: 0
                            }}
                        />
                    ) : (
                        <DesktopIcon 
                            style={{ 
                                width: iconSize, 
                                height: iconSize,
                                minWidth: iconSize,
                                minHeight: iconSize,
                                transition: 'all 0.3s ease',
                                flexShrink: 0
                            }}
                        />
                    )}
                    <ExpandingText>Switch Theme</ExpandingText>
                </button>
            </div>
        </div>
    );
    
    return (
        <>
            {/* Mobile Sidebar */}
            {isMobileOpen && (
                <div className="fixed inset-0 z-40 lg:hidden">
                    <div className="absolute inset-0 bg-black/60" onClick={() => setMobileOpen(false)}></div>
                    <div className="relative w-48 h-full transition-transform duration-300 transform translate-x-0">
                        {sidebarContent}
                    </div>
                </div>
            )}
            {/* Desktop Sidebar */}
            <div className={`hidden lg:flex lg:flex-shrink-0 transition-all duration-300 ${isExpanded ? 'w-48' : 'w-20'}`}>
                <div className="w-full h-full">
                    {sidebarContent}
                </div>
            </div>
        </>
    );
};

export default Sidebar;