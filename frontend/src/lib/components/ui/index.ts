import * as Alert from "./alert";
import * as Badge from "./badge";
import * as Button from "./button";
import * as Card from "./card";
import * as Input from "./input";
import * as Label from "./label";
import * as Select from "./select";
import * as Separator from "./separator";
import * as Slider from "./slider";
import * as Switch from "./switch";
import * as Tabs from "./tabs";
import * as Textarea from "./textarea";

// Re-export as namespaces for bulk imports like import { Button, Input } from '$lib/components/ui'
export {
    Alert,
    Badge,
    Button,
    Card,
    Input,
    Label,
    Select,
    Separator,
    Slider,
    Switch,
    Tabs,
    Textarea,
};

// Also export individual components for convenience if needed, 
// though shadcn-svelte traditionally uses the namespaced version.
export { Root as BadgeComponent } from "./badge";
export { Root as ButtonComponent, buttonVariants } from "./button";
export { Root as InputComponent } from "./input";
export { Root as LabelComponent } from "./label";
export { Root as TextareaComponent } from "./textarea";
export { Root as SwitchComponent } from "./switch";

// Custom components
export { default as LoadingSpinner } from "./LoadingSpinner.svelte";
