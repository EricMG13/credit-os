import type { ComponentPropsWithRef, ReactNode } from "react";
import { createContext, useContext } from "react";
import type {
  TabListProps as AriaTabListProps,
  TabProps as AriaTabProps,
  TabRenderProps as AriaTabRenderProps,
} from "react-aria-components";
import {
  Tab as AriaTab,
  TabList as AriaTabList,
  TabPanel as AriaTabPanel,
  Tabs as AriaTabs,
  TabsContext,
  useSlottedContext,
} from "react-aria-components";
import { Badge } from "@/components/base/badges/badges";
import { cx } from "@/utils/cx";

type Orientation = "horizontal" | "vertical";

// Types for different orientations
type HorizontalTypes = "underline";
type VerticalTypes = "line";
type TabTypeColors<T> = T extends "horizontal" ? HorizontalTypes : VerticalTypes;
type TabType = HorizontalTypes | VerticalTypes;

// Styles for different types of tab
const getTabStyles = ({ isFocusVisible, isSelected, isHovered }: AriaTabRenderProps) => ({
  underline: cx(
    "rounded-none border-b-2 border-transparent outline-focus-ring",
    isFocusVisible && "outline-2 -outline-offset-2",
    (isSelected || isHovered) && "border-fg-brand-primary_alt text-brand-secondary",
  ),
  line: cx(
    "rounded-none border-l-2 border-transparent outline-focus-ring",
    isFocusVisible && "outline-2 -outline-offset-2",
    (isSelected || isHovered) && "border-fg-brand-primary_alt text-brand-secondary",
  ),
});

const sizes = {
  sm: {
    base: "text-sm font-semibold gap-1",
    underline: "px-0.5 pb-2.5 pt-0",
    line: "pl-2.5 pr-3 py-0.5",
  },
  md: {
    base: "text-md font-semibold gap-1.5",
    underline: "px-0.5 pb-2.5 pt-0",
    line: "pr-3.5 pl-3 py-1",
  },
};

// Styles for the tab list of each type
const listStyles = {
  underline: "gap-3",
  line: "gap-2",
};

interface TabListComponentProps<K extends Orientation> extends AriaTabListProps<object> {
  /** The size of the tab list. */
  size?: keyof typeof sizes;
  /** The type of the tab list. */
  type?: TabTypeColors<K>;
  /** The orientation of the tab list. */
  orientation?: K;
}

const TabListContext = createContext<{ size: keyof typeof sizes; type: TabType }>({
  size: "sm",
  type: "underline",
});

export const TabList = <T extends Orientation>({
  size = "sm",
  type = "underline" as TabTypeColors<T>,
  orientation: orientationProp,
  className,
  children,
  ...otherProps
}: TabListComponentProps<T>) => {
  const context = useSlottedContext(TabsContext);

  const orientation = orientationProp ?? context?.orientation ?? "horizontal";

  return (
    <TabListContext.Provider value={{ size, type }}>
      <AriaTabList
        {...otherProps}
        className={(state) =>
          cx(
            "group flex",

            listStyles[type],

            orientation === "vertical" && "w-max flex-col",

            // Only horizontal tabs with underline type have bottom border
            orientation === "horizontal" &&
              type === "underline" &&
              "relative before:absolute before:inset-x-0 before:bottom-0 before:h-px before:bg-border-secondary",

            typeof className === "function" ? className(state) : className,
          )
        }
      >
        {children}
      </AriaTabList>
    </TabListContext.Provider>
  );
};

export const TabPanel = (props: ComponentPropsWithRef<typeof AriaTabPanel>) => {
  return (
    <AriaTabPanel
      {...props}
      className={(state) =>
        cx(
          "outline-focus-ring focus-visible:outline-2 focus-visible:outline-offset-2",
          typeof props.className === "function" ? props.className(state) : props.className,
        )
      }
    />
  );
};

interface TabComponentProps extends Omit<AriaTabProps, "children"> {
  /** The label of the tab. */
  children?: ReactNode;
  /** The badge displayed next to the label. */
  badge?: string;
}

export const Tab = ({ children, badge, className, ...otherProps }: TabComponentProps) => {
  const { size, type } = useContext(TabListContext);

  return (
    <AriaTab
      {...otherProps}
      className={(prop) =>
        cx(
          "z-10 flex h-max cursor-pointer items-center justify-center gap-2 rounded-md whitespace-nowrap text-quaternary transition duration-100 ease-linear",
          "group-orientation-vertical:justify-start",
          sizes[size].base,
          sizes[size][type],
          getTabStyles(prop)[type],
          typeof className === "function" ? className(prop) : className,
        )
      }
    >
      <span className={cx("flex items-center gap-1.5", type !== "line" && "px-0.5")}>
        {children}

        {/* Badge */}
        {badge && (
          <Badge
            size="sm"
            color="gray"
            className={cx("hidden transition-inherit-all md:flex", size === "sm" && "-my-px")}
          >
            {badge}
          </Badge>
        )}
      </span>
    </AriaTab>
  );
};

export const Tabs = ({ className, ...props }: ComponentPropsWithRef<typeof AriaTabs>) => {
  return (
    <AriaTabs
      keyboardActivation="manual"
      {...props}
      className={(state) =>
        cx("flex w-full flex-col", typeof className === "function" ? className(state) : className)
      }
    />
  );
};

Tabs.Panel = TabPanel;
Tabs.List = TabList;
Tabs.Item = Tab;
